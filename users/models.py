from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.conf import settings

# Create your models here.

#Code written by me
class AppUserManager(BaseUserManager):
    #code based on Django's main project github (guide)'s instructions: https://github.com/django/django/blob/main/django/contrib/auth/models.py#L128
    def create_user(self, email, username, firstname, lastname, password, **extra_fields):
        if not email:
            raise ValueError('Please provide an appropriate email address')

        #Normalize ensures that the email address is in a consistent format by lowercasing the domain name and removing any spaces or other characters. This can be useful in preventing errors when searching or sorting data by email address. It's from BaseUserManager.
        email = self.normalize_email(email)

        # is_staff is a built-in boolean attribute of the Django User model
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        # self.model refers to the user model that is being managed by the manager class. this model is the AppUser model below, which references objects = AppUserManager().
        appuser = self.model(email=email, username=username, firstname=firstname, lastname=lastname, **extra_fields)
        appuser.set_password(password)
        appuser.save()
        return appuser

    #code taken from Django's main project github (guide)'s instructions: https://github.com/django/django/blob/main/django/contrib/auth/models.py#L128 Basically BaseUserManager does not have any method called create_superuser, so its necessary to add this, otherwise would have error when doing python manage.py createsuperuser to create super user. Please see: https://stackoverflow.com/questions/54989276/user-manager-object-has-no-attribute-create-superuser
    def create_superuser(self, email, username, firstname, lastname, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, firstname, lastname, password, **extra_fields)


class AppUser(AbstractBaseUser, PermissionsMixin):
    id = models.BigAutoField(primary_key=True)
    email = models.EmailField(max_length=255, unique=True)
    username = models.CharField(max_length=150, unique=True)
    firstname = models.CharField(max_length=150, blank=False, null=False)
    lastname = models.CharField(max_length=150, blank=False, null=False)
    is_staff = models.BooleanField(default=False)
    #is_active is built-in
    is_active = models.BooleanField(default=True)
    is_oneline = models.BooleanField(default=False)
    organisation = models.ForeignKey("Organisation", on_delete=models.SET_NULL, null=True, blank=True, related_name="appusers")

    objects = AppUserManager()

    #  email is not included in REQUIRED_FIELDS because it is already defined as the USERNAME_FIELD. 
    #Because I defined the USERNAME_FIELD as email here, the simple default JWT authentication takes in email as the username when user requests for token. 
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'firstname', 'lastname']
    EMAIL_FIELD = 'email'

    # same as __unicode__(self) is used in Python 2.x. We overwrite the string dunder method
    def __str__(self):
        return self.email

    #this default get username allows you to get username, this is provided by default django
    #get_username()

    def get_full_name(self):
        return f"{self.firstname} {self.lastname}"


class Friendship(models.Model):
    #[self]one to one field cuz one appuser can only have one entry appuser. Note that one row/entry represents one "friend list" for the relevant appuser
    appuser = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friendship")

    #symetrical false is to make sure ocan't add themselves as friends. 
    appfriends = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="appfriends", symmetrical=False ) 

    def __str__(self):
        return self.appuser.email

    def username(self):
        return self.appuser.username

class AddRequest(models.Model):
    #[self] foreignkey rather than one to one cuz one AppUser instance can have many userfrom entries (more like one to many) in the table.

    #settings.Auth User Model means it is linked to the AppUser model defined above. This is an instance of AppUser. Note that when working with ForeignKeys, they are represented as model instances. But when you serialise a model, the ForeignKey is usually serialised to the ID of the related object.
    user_from = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_from")

    user_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_to")

    date_time = models.DateTimeField(auto_now_add=True)

    ongoing = models.BooleanField(blank=False, default=True, null=False)

    def __str__(self):
        return self.user_from.email


class Profile(models.Model):

    appuser = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    status = models.TextField(blank=True, null=True)
    aboutme = models.TextField(blank=True, null=True)  
    citytown = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)    
    age = models.IntegerField(blank=True, null=True)

    gender = models.CharField(max_length=2, 
    choices=[
        ('M', 'Male'),
        ('F', 'Female'),
        ('NA', 'Unspecified'),
    ], 
    default='NA') 

    def __str__(self):
        return self.appuser.email

class Like(models.Model):
    user_from = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_from_likes")
    user_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_to_likes")
    like_count = models.PositiveIntegerField(default=1)
    last_like_date = models.DateTimeField(auto_now_add=True)

    #note Meta is not only for views.py, it is used for defining metadata for Model too, e.g. constraints, ordering, table name.
    class Meta:
        #the combination of user_from and user_to must be unique
        unique_together = ['user_from', 'user_to']

    #clean is a built in method in model class meant for validation at the model level. it isn't run automatically when .save() so must call it explicitly.
    def clean(self):
        #check that user can't like themself
        if self.user_from == self.user_to:
            raise ValidationError("User cannot like themself!")

    #override .save to trigger clean() validation before saving
    def save(self, *args, **kwargs):
        self.clean()
        #super() is the parent class of the Like model, which is models.Model in django. This line is calling the save method of the parent class (models.Model), ensuring that the instance is saved properly in the database.
        #this is cuz Like model itselt doesn't handle database operations
        #this is what needs to be done if overriding save like in this case.
        super().save(*args, **kwargs)



# may need to link this to user email sufix later
class Organisation(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    citytown = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    #to get reverse: all appusers associated with the organisation in question.
    # org = Organisation.objects.get(name="Strawberry Corp")
    # org_members = org.appusers.all() 








#my code ends here






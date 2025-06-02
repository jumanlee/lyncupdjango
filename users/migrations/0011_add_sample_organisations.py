from django.db import migrations


def add_sample_organisations(apps, schema_editor):
    Country = apps.get_model('users', 'Country')
    Organisation = apps.get_model('users', 'Organisation')

    def get_country(name: str):
        # assumes your add_countries migration has already run
        # this will raise if you mistype the country name
        return Country.objects.get(name=name)

    samples = [
        # Letter, Organisation name, Country
        ("A", "Apple",              "United States"),
        ("B", "BP",                 "United Kingdom"),
        ("C", "Coca-Cola",          "United States"),
        ("D", "Diageo",             "United Kingdom"),
        ("E", "Exxon Mobil",        "United States"),
        ("F", "Facebook",           "United States"),
        ("G", "Google",             "United States"),
        ("H", "HSBC",               "United Kingdom"),
        ("I", "IBM",                "United States"),
        ("J", "Johnson & Johnson",  "United States"),
        ("K", "Kellogg's",          "United States"),
        ("L", "LVMH",               "France"),
        ("M", "Microsoft",          "United States"),
        ("N", "Nestlé",             "Switzerland"),
        ("O", "Oracle",             "United States"),
        ("P", "Procter & Gamble",   "United States"),
        ("Q", "Qualcomm",           "United States"),
        ("R", "Rolls-Royce",        "United Kingdom"),
        ("S", "Sony",               "Japan"),
        ("T", "Tesla",              "United States"),
        ("U", "Unilever",           "United Kingdom"),
        ("V", "Visa",               "United States"),
        ("W", "Walmart",            "United States"),
        ("X", "Xerox",              "United States"),
        ("Y", "Yum! Brands",        "United States"),
        ("Z", "Zara",               "Spain"),
    ]

    for _, org_name, country_name in samples:
        country = get_country(country_name)
        Organisation.objects.get_or_create(
            name=org_name,
            defaults={"country": country},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_remove_organisation_citytown_remove_profile_citytown_and_more'),
    ]

    operations = [
        migrations.RunPython(add_sample_organisations),
    ]

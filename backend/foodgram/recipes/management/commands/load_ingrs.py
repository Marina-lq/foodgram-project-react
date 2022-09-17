import json

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Load ingredients from json'

    def handle(self, *args, **options):
        db_objects = []
        with open('ingredients.json') as f:
            data = json.load(f)

            for ingredient_data in data:
                db_objects.append(
                    Ingredient(**ingredient_data)
                )

        Ingredient.objects.bulk_create(db_objects)

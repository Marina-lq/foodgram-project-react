import csv

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


SUCCESS_MSG = 'Ингредиенты выгружены.'
FAILURE_MSG = 'Выгрузка ингредиентов прошла неудачно.'


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из csv-файла'

    def handle(self, *args, **kwargs):
        try:
            with open('data/ingredients.csv', 'r', encoding='UTF-8') as file:
                for row in csv.reader(file):
                    Ingredient.objects.get_or_create(
                        name=row[0], measurement_unit=row[1],
                    )
            self.stdout.write(self.style.SUCCESS(SUCCESS_MSG))
        except Exception:
            self.stdout.write(self.style.ERROR(FAILURE_MSG))

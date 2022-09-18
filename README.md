Foodgram - сервис, где каждый может публиковать свои самые вкусные рецепты, 

подписываться на других авторов и добавлять рецепты в избранное и список покупок.

Проверить работу можно по адресу http://158.160.3.36/

Тестовые данные администратора: email: lq-sun@mail.ru password: 2222

Подготовка и запуск проекта

Клонируйте репозиторий

https://github.com/Marina-lq/foodgram-project-react

Создайте и активируйте виртуальное окружение

python -m venv venv

source venv/Scripts/activate

Перейдите в папку infra

cd infra/

Запустите команду для сборки контейнеров

docker-compose up -d

Внутри контейнера web примените миграции, 

соберите статику, 

загрузите ингредиенты и создайте суперпользователя

docker-compose exec web bash

python manage.py makemigrations

python manage.py migrate

python manage.py collectstatic

python manage.py load_ingredients

python manage.py createsuperuser

Теперь сайт доступен по адресу localhost

Дополнительно

Чтобы иметь возможность создавать свои рецепты, 

создайте необходимые вам теги для рецептов в админ-панели Django.

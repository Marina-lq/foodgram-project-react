Продуктовый помощник Foodgram

«Продуктовый помощник»: приложение, на котором пользователи публикуют рецепты, подписываться на публикации других авторов и добавлять рецепты в избранное. Сервис «Список покупок» позволит пользователю создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

Запуск проекта через Docker
В папке infra выполнить команду, что бы собрать контейнер:
sudo docker-compose up -d
Для доступа к контейнеру выполните следующие команды:

sudo docker-compose exec backend python manage.py makemigrations
sudo docker-compose exec backend python manage.py migrate --noinput
sudo docker-compose exec backend python manage.py createsuperuser
sudo docker-compose exec backend python manage.py collectstatic --no-input
Дополнительно можно наполнить DB ингредиентами и тэгами:

sudo docker-compose exec backend python manage.py load_tags
sudo docker-compose exec backend python manage.py load_ingrs

Запуск проекта в dev-режиме
Установить и активировать виртуальное окружение
source /venv/bin/activated

Установить зависимости из файла requirements.txt
python -m pip install --upgrade pip
pip install -r requirements.txt

Выполнить миграции:
python manage.py migrate

В папке с файлом manage.py выполнить команду:
python manage.py runserver
Документация к API доступна после запуска

http://127.0.0.1/api/docs/
Автор: Судоплатова Марина

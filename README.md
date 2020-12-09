# ETL_sprint_2.5

ETL-процесс для перекачки данных из Poestgresql в Elasticsearch


 Наименования в моей схеме БД отличаются от тех, что используются в курсе. 
Для полноценного тестирования необходимо поднять базу с помощью репозитория https://github.com/jakkemomo/Admin_panel_sprint_1 

Заполнить .env файл данными для подключения к постгресу и sqlite.
Выполнить несколько команд для создания схемы, перегрузки данных в постгрес:
1. python schema_design/schema.py
2. python sqlite_to_postgres/load_data.py

Операции в рамках этого репозитория:
1. Создать .env файл
2. pip install -r requirements.txt
3. Запустить es и добавить в него схему из schema.txt
4. etl.py
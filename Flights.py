import streamlit as st
import requests
import json
import calendar
import pytz
import pandas as pd
from datetime import datetime, timedelta
from openpyxl import load_workbook
import networkx as nx

hide_decoration_bar_style = '''
    <style>
        header {visibility: hidden;}
    </style>
'''
st.markdown(hide_decoration_bar_style, unsafe_allow_html=True)

st.title('Генератор DH')
st.subheader('на основе Яндекс.Расписания')

file = st.file_uploader("Файл с расписанием", type="json")
if file is not None:
    bytes_datastr = file.read()
    bytes_databyte = file.getvalue()
    filename = file.name
    st.write(f'Загружен файл `{filename}`')
    
url_airports = 'https://api.travelpayouts.com/data/ru/airports.json'

response_airports = requests.get(url_airports)
data_airports = json.loads(response_airports.text)

airport_codes = []

for airport in data_airports:
    airport_codes.append([airport['code'], airport['time_zone']])

def get_time_zone(code):
    for airport in airport_codes:
        if airport[0] == code:
            return airport[1]

Base_airline = st.sidebar.text_input("Код базовой авиакомпании", "H4")
api_key = st.sidebar.text_input("API Ключ Яндекс.Расписания", "")

first_array = st.sidebar.text_input("Аэропорт(ы) набор 1", "LED")
second_array = st.sidebar.text_input("Аэропорт(ы) набор 2", "SVX KJA")

tuples = []

for element1 in first_array.split(' '):
    for element2 in second_array.split(' '):
        tuples.append((element1, element2))
        tuples.append((element2, element1))


#start_date = st.date_input(label='Начальная дата', key='start_date')
#end_date = st.date_input(label='Конечная дата', key='end_date')

start_date = datetime.now()
end_date = datetime.now() + timedelta(days=1)
start_date, end_date = st.date_input('Период (доступно до 30 дней назад и 11 месяцев вперед от текущей даты)', [start_date, end_date])
if start_date < end_date:
    pass
else:
    st.error('Неверный диапазон дат')


# определяем окно для выбора подходящих рейсов для ДХ. Указываем в минутах
# берем те рейсы, которые улетают из аэропорта, куда прилетел рейс в течение окна, указанного в минутах ниже
st.markdown('<style> .stSlider > div { width: 100%; } </style>', unsafe_allow_html=True)
start_window, end_window = st.slider('Окно поиска DH относительно прилёта', 0, 1440, (0, 1440))


edges = tuples
with st.expander("Проверить рейсы"):
    st.sidebar.write(edges)

if st.button('Сгенерировать'):
    # Последовательно обрабатывваем все ребра из графа расписания
    # counter - затычка, чтобы ограничить кол-во запросов для тестовых нужд
    #counter = 0
    for edge in edges:
        final_array = []
        #if counter == 3:
        #    break
        #counter += 1
        # Формируем массив-выборку на конкретную дату
        airportDEP = edge[0]
        airportARR = edge[1]
        if airportDEP == airportARR:
            continue

        print(f'---------------Начинаем работать с плечом {airportDEP}-{airportARR}-------------------')
        data = json.loads(bytes_datastr)

        for i in range((end_date - start_date).days + 1):
            current_day = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            print(current_day)


            print(f'-----------Обрабатываем плечи на дату: {current_day}')

            # Параметры запроса
            format = 'json'
            lang = 'ru_RU'
            transport_types = 'plane'
            system = 'iata'
            transfers = 'false'
            result_timezone = 'UTC'

            # подготавливаем запрос в Я.Расписание
            dep = airportDEP
            arr = airportARR
            # в 2021 году аэропорт Гянджи поменял свой код - учитываем это
            if airportDEP == 'KVD':
                dep = 'GNJ'
            if airportARR == 'KVD':
                arr = 'GNJ'
            date = current_day
            print(date)

            # Запрашиваем....
            url = f'https://api.rasp.yandex.net/v3.0/search/?apikey={api_key}&transport_types={transport_types}&system={system}&transfers={transfers}&result_timezone={result_timezone}&format={format}&from={dep}&to={arr}&date={date}&lang={lang}&page=1'
            response = requests.get(url)

            print(url)

            # Выводим в консоль
            print(response.json())

            # Делаем массив из ответа Яндекса
            # Делаем матрицу подходящих рейсов для ДХ - Добавляем в список перспективных рейсов для ДХ - массив Б (Авиакомпания, Порт Отправление, Порт Прибытие, Дата-Время отправления, Дата-Время прибытия)

            ya_data = response.json()

            # Инициализиуерм массив для записи ответа яндекса
            ya_flights_data = []

            # Проходим по JSON - ответу Яндекса
            for segment in ya_data['segments']:
                iata_code = segment['thread']['carrier']['codes']['iata']
                # отфильтровываем рейсы U6
                if iata_code != Base_airline:
                    departure_code = dep #segment['from']['code']
                    arrival_code = arr #segment['to']['code']
                    departure_time = segment['departure']
                    arrival_time = segment['arrival']
                    number = segment['thread']['number']
                    #number = number[3:]
                    ya_flights_data.append([iata_code, departure_code, arrival_code, departure_time, arrival_time, number])

            print('Массив на базе Яндекса:')
            print(ya_flights_data)

            print(f'Количество ДХ из {airportDEP} в {airportARR} в дату {current_day}: ')
            print(len(ya_flights_data))

            sub_final_array = []

            if ya_flights_data is not None:
                if final_array is not None:

                    final_array += ya_flights_data
                    print('11111')
                    print(ya_flights_data)
                    print(final_array)
                else:
                    #final_array = ya_flights_data
                    print('22222')

        # Добавление новых ДХ в исходный файл
        if final_array is not None:
            for entry in final_array:
                new_flight = {}
                new_flight['id'] = entry[3][:10].replace("-", "") + '-' + entry[5][:2] + '-' + entry[1] + '-' + entry[5][3:]
                new_flight['active'] = True
                new_flight['airlineDesignator'] = entry[0]
                new_flight['number'] = entry[5][3:]
                new_flight['operationalSuffix'] = ''
                #new_flight['legCount'] = 'null'
                new_flight['legSeqNumber'] = None
                new_flight['aircraftType'] = '737'
                new_flight['departureAirportCode'] = entry[1]
                new_flight['arrivalAirportCode'] = entry[2]
                new_flight['serviceType'] = 'J'

                date_time = datetime.strptime(entry[3], '%Y-%m-%dT%H:%M:%S%z')
                date_time = date_time - timedelta(days=243)

                new_flight['departureDateUtc'] = date_time.strftime('%Y-%m-%dT%H:%M:%SZ')

                date_time = datetime.strptime(entry[4], '%Y-%m-%dT%H:%M:%S%z')
                date_time = date_time - timedelta(days=243)

                new_flight['arrivalDateUtc'] = date_time.strftime('%Y-%m-%dT%H:%M:%SZ')

                # берем код аэропорта вылета, ищем его в массиве с аэропортами, получаем часовой пояс, добавляем к базовому времени

                time_obj = datetime.strptime(entry[3], '%Y-%m-%dT%H:%M:%S%z')
                tz = pytz.timezone(get_time_zone(entry[1]))
                time_obj = time_obj.astimezone(tz)
                time_obj = time_obj - timedelta(days=243)
                local_datetime = time_obj.strftime('%Y-%m-%dT%H:%M:%S')

                new_flight['dateTimeDepartureLocal'] = local_datetime
        
                print(f'Добавляем запись: {new_flight}')
                data['flights'].append(new_flight)

            bytes_datastr = json.dumps(data)

        else:
            print('Финальный массив пуст, записывать нечего')

        data = []

        
        print(f'---------------Закончили работать с плечом {airportDEP}-{airportARR}-------------------')
    with st.expander("Итоговый набор плеч"):
        st.write(final_array)

    
    btn = st.download_button(label="Скачать файл",
                    data=bytes_datastr,
                    file_name=filename.replace('.json','_DH.json'),
                    mime="JSON")

    

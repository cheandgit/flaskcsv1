from flask import Flask, render_template, jsonify
import pandas as pd
import os
# ----------------------------------------------------------
# main5.py - 5-я версия - index5.html
# ----------------------------------------------------------
# Город с учетом штата
# ----------------------------------------------------------
# | № | Город (штат) | Количество заказов | Выручка | Доля, % 
# ----------------------------------------------------------
# - Остальные города
# - Сводная информация
# - Для круговой диаграммы (без изменений - как main3.py)
# - Сравнение двух городов: get_metadata(), def get_sales_comparison()
# - Поправлено для столбиковой диаграммы
# ----------------------------------------------------------

app = Flask(__name__)

def read_file(file_path):
    """Чтение CSV файла"""
    return pd.read_csv(file_path, encoding='utf-8')

def get_sales_data(dataset, year):
    """Выручка по городам за конкретный год с учетом штата"""
    year_data = dataset[dataset['order_date'].str[:4] == year].copy()
    # Группируем по городу и штату вместе
    result = year_data.groupby(['city', 'state'], as_index=False).agg(
        count=('order_date', 'count'), 
        sales=('sales', 'sum')
    )
    # Создаем объединенное название "Город, Штат"
    result['city_state'] = result['city'] + ', ' + result['state']
    return result.sort_values('sales', ascending=False)    

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/api/data/sales-by-city/<year>')
def get_sales_by_city(year):
    """Выручка и доля по городам за год"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'orders_customers.csv')
        df = read_file(file_path)
        sales_year = get_sales_data(df, year)
        
        total_sales = sales_year['sales'].sum()
        sales_year['share'] = (sales_year['sales'] / total_sales * 100).round(2)
        top10 = sales_year.head(10)
        others_sales = total_sales - top10['sales'].sum()

        return jsonify({
            'year': year,
            # 'records' указывает, что получаем список словарей, где каждый словарь соответствует строке DataFrame, 
            # и ключами являются названия колонок.
            'top_cities': top10.to_dict('records'),
            'total_sales': float(total_sales),
            'others_sales': float(others_sales)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/api/data/metadata')
def get_metadata():
    """Метаданные - списки городов (с учетом штата) и годов"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'orders_customers.csv')
        df = read_file(file_path)
        
        # Создаем список городов в формате "Город, Штат"
        cities_with_state = sorted((df['city'] + ', ' + df['state']).unique().tolist())
        
        years = sorted(df['order_date'].str[:4].unique().tolist())
        
        return jsonify({
            'cities': cities_with_state,
            'years': years
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# @app.route('/api/data/metadata')
# def get_metadata():
#     """Метаданные - списки городов и годов"""
#     try:
#         file_path = os.path.join(os.path.dirname(__file__), 'orders_customers.csv')
#         df = read_file(file_path)
        
#         cities = sorted(df['city'].unique().tolist())
#         years = sorted(df['order_date'].str[:4].unique().tolist())
        
#         return jsonify({
#             'cities': cities,
#             'years': years
#         })
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

@app.route('/api/data/comparison')
def get_sales_comparison():
    """Данные для сравнения двух городов по годам с учетом штата"""
    from flask import request
    city_state1 = request.args.get('city1')  # Формат: "Город, Штат"
    city_state2 = request.args.get('city2')  # Формат: "Город, Штат"

    if not city_state1 or not city_state2:
        return jsonify({'error': 'Необходимо указать два города для сравнения'}), 400

    try:
        file_path = os.path.join(os.path.dirname(__file__), 'orders_customers.csv')
        df = read_file(file_path)
        
        # Разделяем "Город, Штат" на отдельные компоненты
        def split_city_state(city_state):
            parts = city_state.split(', ')
            if len(parts) != 2:
                raise ValueError(f"Неверный формат города: {city_state}. Ожидается: 'Город, Штат'")
            return parts[0].strip(), parts[1].strip()
        
        city1, state1 = split_city_state(city_state1)
        city2, state2 = split_city_state(city_state2)
        
        # Фильтруем данные с учетом и города, и штата
        comparison_df = df[
            ((df['city'] == city1) & (df['state'] == state1)) | 
            ((df['city'] == city2) & (df['state'] == state2))
        ].copy()
        
        comparison_df['year'] = comparison_df['order_date'].str[:4]
        
        # ==================================================
        # 1-я версия - рабочая
        # # Агрегируем продажи по годам и городам (с учетом штата)
        # sales_by_year = comparison_df.groupby(['year', 'city', 'state'])['sales'].sum().reset_index()
        
        # # Создаем объединенные названия для отображения
        # sales_by_year['city_label'] = sales_by_year['city'] + ' (' + sales_by_year['state'] + ')'
        
        # # Желаемый порядок городов, преобразуем в формат 'Город (Штат)'
        # desired_order = [
        #     city_state1.replace(', ', ' (') + ')',
        #     city_state2.replace(', ', ' (') + ')']

        # # Преобразуем в широкий формат для Chart.js
        # sales_pivot = sales_by_year.pivot_table(
        #     index='year', 
        #     columns='city_label', 
        #     values='sales', 
        #     aggfunc='sum'
        # ).fillna(0)
        # # Выставляем порядок столбцов согласно desired_order
        # sales_pivot = sales_pivot[desired_order]
        # ==================================================
        # 2-я версия - немого прощённый вариант
        # Создаем объединенное название 'Город (Штат)' и агрегируем продажи по годам и городу
        sales_by_year = (
            comparison_df.assign(city_label=lambda df: df['city'] + ' (' + df['state'] + ')')
            .groupby(['year', 'city_label'])['sales']
            .sum()
            .reset_index()
        )
        # Формируем desired_order в требуемом формате сразу
        desired_order = [f"{city} ({state})" for city, state in (c.split(', ') for c in [city_state1, city_state2])]
        # Преобразуем в широкий формат для Chart.js и ставим нужный порядок столбцов
        sales_pivot = sales_by_year.pivot(index='year', columns='city_label', values='sales').fillna(0)
        sales_pivot = sales_pivot[desired_order]
        # ==================================================

        # Формируем ответ
        response_data = {
            'years': sales_pivot.index.tolist(),
            'datasets': [
                {
                    'label': col, 
                    'data': sales_pivot[col].tolist()
                } for col in sales_pivot.columns
            ]
        }
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# @app.route('/api/data/comparison')
# def get_sales_comparison():
#     """Данные для сравнения двух городов по годам"""
#     from flask import request
#     city1 = request.args.get('city1')
#     city2 = request.args.get('city2')

#     if not city1 or not city2:
#         return jsonify({'error': 'Необходимо указать два города для сравнения'}), 400

#     try:
#         file_path = os.path.join(os.path.dirname(__file__), 'orders_customers.csv')
#         df = read_file(file_path)
        
#         # Фильтруем данные только для двух выбранных городов
#         comparison_df = df[df['city'].isin([city1, city2])].copy()
#         comparison_df['year'] = comparison_df['order_date'].str[:4]

#         # Агрегируем продажи по годам и городам
#         sales_by_year = comparison_df.groupby(['year', 'city'])['sales'].sum().unstack().fillna(0)

#         # Формируем ответ
#         response_data = {
#             'years': sales_by_year.index.tolist(),
#             'datasets': [{'label': city, 'data': sales_by_year[city].tolist()} for city in sales_by_year.columns]
#         }
#         return jsonify(response_data)
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
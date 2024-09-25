from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup
import sqlite3
import re
from datetime import datetime

# URL do site 
url = 'https://www.terra.com.br/vida-e-estilo/turismo/agenda-das-melhores-festas-juninas-do-rio-de-janeiro-em-2024,bc6a7d20eb8387a655d260b9ae4167a9ma2y7qa1.html'

# Requisição HTTP com tratamento de erro
try:
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(req) as response:
        html = response.read()
except HTTPError as e:
    print(f'Erro HTTP: {e.code}')
except URLError as e:
    print(f'Erro de URL: {e.reason}')

# Usando BeautifulSoup para transformar o HTML em um objeto que pode ser manipulado
soup = BeautifulSoup(html, 'html.parser')

# Dicionário para adicionar a informação sobre se cada evento é ao ar livre ou não
# True = é ao ar livre, False = não é ao ar livre
ar_livre_info = {
    'Arraiá Raiz': False,
    'Arraiá Encontro de Rodas': True,
    'Arraiá Samba de Santa': True,
    'Festa Junina da Lagoa': True,
    'Arraiá do Rio': True,
    'Arraiá da Feira Moderna': True,
    'Arraiá do Bem': False,
    'Carioquíssima na Roça': True,
    'Arraiá da Fundição': False,
    'Arraial Mundo Bita': False,
    'Arraiá da Amazônia': False,
    'Junina da Urca': True,
    'Arraiá Downtown': True,
    'Arraiá do Circo': False
}

# Função para limpar e extrair apenas as datas
def extrair_datas(texto):
    '''
    Extrai datas no formato 'd de mês' ou 'dd de mês' do texto

    Argumento: texto contendo as datas a serem extraídas

    Returno: string contendo as datas extraídas separadas por ' a '
    '''
    datas = re.findall(r'\d{1,2}º? de [a-zç]+', texto) # Regex para encontrar padrões de datas
    return ' a '.join(datas)

# Função para converter data para formato YYYY-MM-DD
def converter_data(texto):
    '''
    Converte datas no formato 'd de mês' ou 'dd de mês' para o formato YYYY-MM-DD

    Argumento: texto contendo as datas a serem convertidas

    Returno: lista contendo as datas no formato YYYY-MM-DD
    '''
    # Dicionário para mapear os nomes dos meses para seus respectivos números
    meses = {
        'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
        'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
        'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
    }
    datas = re.findall(r'(\d{1,2})º? de ([a-zç]+)', texto) # Regex para encontrar padrões de datas
    datas_convertidas = []
    for dia, mes in datas:
        mes_num = meses[mes]
        ano = '2024'  # Ano fixo
        data_formatada = f'{ano}-{mes_num}-{int(dia):02d}' # Cria uma string no formato YYYY-MM-DD
        datas_convertidas.append(data_formatada)
    return datas_convertidas

# Lista para armazenar os dados dos eventos
eventos = []

# Extração dos dados dos eventos
artigo = soup.find('div', class_='article__content--body article__content--internal') # BeautifulSoup para encontrar a div principal que tem o corpo do artigo, identificada pela classe específica 
blocos = artigo.find_all(['h3', 'p', 'blockquote']) # Encontra todos os elementos h3 e p dentro da div principal

evento_atual = {}
for bloco in blocos:
    if bloco.name == 'h3': 
        if evento_atual: # Se o bloco é um título h3, verifica se evento_atual já possui dados
            eventos.append(evento_atual) # Se possui, adiciona à lista
        evento_atual = {'nome': bloco.text.strip(), 'metadados': []} # Inicializa um novo evento_atual com o nome do evento e uma lista vazia para metadados
    elif bloco.name == 'p':
        text = bloco.text.strip() # Se o bloco é um parágrafo p, verifica o texto
        if text.startswith('Quando?'):
            datas_extraidas = extrair_datas(text.replace('Quando? ', ''))
            datas_convertidas = converter_data(datas_extraidas)
            evento_atual['data'] = datas_convertidas[0] if datas_convertidas else '' # Se o texto começa com 'Quando?', extrai e converte as datas e as adiciona a evento_atual
        elif text.startswith('Onde?'):
            evento_atual['localizacao'] = text.replace('Onde? ', '') + ' - RJ' # Se o texto começa com 'Onde?', extrai a localização e a adiciona a evento_atual
    elif bloco.name == 'blockquote':
        instagram_link = bloco.find('a')['href']
        evento_atual['metadados'].append(instagram_link) # Se o bloco é uma citação blockquote, extrai o link do Instagram dos evento que possuem e o adiciona aos metadados de evento_atual

if evento_atual:
    eventos.append(evento_atual) # Adiciona o último evento_atual à lista eventos se não estiver vazio

# Conexão com o banco de dados
conn = sqlite3.connect('eventos_culturais.db')
cursor = conn.cursor()

# Criação das tabelas Eventos, Dados dos Eventos e Metadados
cursor.execute('''
CREATE TABLE IF NOT EXISTS Eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    tipo TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS DadosEventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER,
    data DATE,
    localizacao TEXT,
    ar_livre BOOLEAN,
    FOREIGN KEY (evento_id) REFERENCES Eventos (id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Metadados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER,
    metadado TEXT,
    FOREIGN KEY (evento_id) REFERENCES Eventos (id)
)
''')

# Inserção dos dados nas tabelas
for evento in eventos:
    cursor.execute('''
    INSERT INTO Eventos (nome, tipo)
    VALUES (?, ?)
    ''', (evento['nome'], 'Festa Junina'))  # Tipo atribuído como 'Festa Junina' para todos

    evento_id = cursor.lastrowid

    cursor.execute('''
    INSERT INTO DadosEventos (evento_id, data, localizacao, ar_livre)
    VALUES (?, ?, ?, ?)
    ''', (evento_id, evento['data'], evento['localizacao'], ar_livre_info[evento['nome']]))

    for metadado in evento['metadados']:
        cursor.execute('''
        INSERT INTO Metadados (evento_id, metadado)
        VALUES (?, ?)
        ''', (evento_id, metadado))

# Commit e fechamento da conexão
conn.commit()
conn.close()

# Função para mostrar todos os eventos armazenados 
def consultar_eventos():
    conn = sqlite3.connect('eventos_culturais.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT Eventos.nome, Eventos.tipo, DadosEventos.data, DadosEventos.localizacao, DadosEventos.ar_livre 
    FROM DadosEventos
    JOIN Eventos ON DadosEventos.evento_id = Eventos.id
    ORDER BY DadosEventos.data ASC
    ''')

    resultados = cursor.fetchall()
    print('Eventos com suas datas, localização, tipo de evento e se é ao ar livre:')
    for row in resultados:
        print(f"Nome: {row[0]}, Tipo: {row[1]}, Data: {row[2]}, Localização: {row[3]}, Ar Livre: {'Sim' if row[4] else 'Não'}")

    conn.close()
consultar_eventos()

# Função para mostrar os dois eventos mais próximos de iniciar
def consultar_eventos_proximos():
    conn = sqlite3.connect('eventos_culturais.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT Eventos.nome, Eventos.tipo, DadosEventos.data, DadosEventos.localizacao, DadosEventos.ar_livre
    FROM DadosEventos
    JOIN Eventos ON DadosEventos.evento_id = Eventos.id
    WHERE DadosEventos.data >= DATE('now')
    ORDER BY DadosEventos.data ASC
    LIMIT 2
    ''')

    resultados = cursor.fetchall()
    print('\nOs dois eventos mais próximos de iniciar:')
    for row in resultados:
        print(f"Nome: {row[0]}, Tipo: {row[1]}, Data: {row[2]}, Localização: {row[3]}, Ar Livre: {'Sim' if row[4] else 'Não'}")

    conn.close()
consultar_eventos_proximos()

# Função para mostrar eventos que acontecem no Rio de Janeiro
def consultar_eventos_rio():
    conn = sqlite3.connect('eventos_culturais.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT Eventos.nome, Eventos.tipo, DadosEventos.data, DadosEventos.localizacao, DadosEventos.ar_livre
    FROM DadosEventos
    JOIN Eventos ON DadosEventos.evento_id = Eventos.id
    WHERE DadosEventos.localizacao LIKE '%- RJ'
    ORDER BY DadosEventos.data ASC
    ''')

    resultados = cursor.fetchall()
    print('\nEventos que acontecem no Rio de Janeiro:')
    for row in resultados:
        print(f"Nome: {row[0]}, Tipo: {row[1]}, Data: {row[2]}, Localização: {row[3]}, Ar Livre: {'Sim' if row[4] else 'Não'}")

    conn.close()
consultar_eventos_rio()

# Função para mostrar eventos que são ao ar livre
def consultar_eventos_ar_livre():
    conn = sqlite3.connect('eventos_culturais.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT Eventos.nome, Eventos.tipo, DadosEventos.data, DadosEventos.localizacao, DadosEventos.ar_livre
    FROM DadosEventos
    JOIN Eventos ON DadosEventos.evento_id = Eventos.id
    WHERE DadosEventos.ar_livre = 1
    ORDER BY DadosEventos.data ASC
    ''')

    resultados = cursor.fetchall()
    print('\nEventos ao ar livre:')
    for row in resultados:
        print(f"Nome: {row[0]}, Tipo: {row[1]}, Data: {row[2]}, Localização: {row[3]}, Ar Livre: {'Sim' if row[4] else 'Não'}")

    conn.close()
consultar_eventos_ar_livre()

# Função para mostrar todos os metadados dos evento
def consultar_metadados():
    conn = sqlite3.connect('eventos_culturais.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT Eventos.nome, Metadados.metadado
    FROM Metadados
    JOIN Eventos ON Metadados.evento_id = Eventos.id
    ''')

    resultados = cursor.fetchall()
    print('\nMetadados por evento:')
    for row in resultados:
        print(f"Evento: {row[0]}, Metadado: {row[1]}")

    conn.close()
consultar_metadados()


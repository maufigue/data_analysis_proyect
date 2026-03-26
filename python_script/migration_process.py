import pandas as pd
from sqlalchemy import create_engine

# Conexión a PostgreSQL
engine = create_engine("postgresql://postgres:mau7@localhost:5433/spaceman_proyect")

# Extraction

# cargar productos
input_productos_file = r"C:\Users\Mauricio Figueredo G\Desktop\data_pipeline\data\raw_data\productos.csv"

df_productos = pd.read_csv(
    input_productos_file,
    sep=";",
    encoding="utf-8",  # por los caracteres raros
    dtype={"subcategoria_nueva": "string"}
)

# cargar tickets
input_tickets_file = r"C:\Users\Mauricio Figueredo G\Desktop\data_pipeline\data\raw_data\tickets.csv"

df_tickets = pd.read_csv(
    input_tickets_file,
    sep=";",
    encoding="utf-8", # por los caracteres raros
    dtype={"ticket": "string"},
    true_values=["true"],
    false_values=["false"]
)

# Transformation

# productos
df_productos.columns = df_productos.columns.str.replace('"', '')

# tickets
df_tickets.columns = df_tickets.columns.str.replace('"', '')

# Load PostgreSQL

print("Filas cargadas en la tabla productos:", len(df_productos))

df_productos.to_sql(
    "productos",
    engine,
    if_exists="append",
    index=False
)

print("Filas cargadas en la tabla tickets:", len(df_tickets))

df_tickets.to_sql(
    "tickets",
    engine,
    if_exists="append",
    index=False
)

print("Proceso Finalizado.")
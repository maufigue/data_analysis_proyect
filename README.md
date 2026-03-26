Proyecto de Análisis Retail – Python + PostgreSQL + Power BI

1. Descripción del Proyecto

Este proyecto tiene como objetivo analizar el desempeño de ventas de dos cadenas de supermercados utilizando datos históricos correspondientes al primer trimestre de 2023 y 2024.

Se desarrolló un pipeline completo de datos que incluye:

Ingesta de archivos CSV
Limpieza y transformación de datos
Almacenamiento en base de datos relacional
Análisis mediante SQL
Visualización interactiva en Power BI

2. Tecnologías Utilizadas
Python >> Procesamiento y migración de datos
PostgreSQL >> Almacenamiento y modelado relacional
SQL >> Consultas analíticas y creación de vistas
Power BI >> Visualización de datos
DAX >> Creación de métricas y tabla calendario
Power Query (M) >> Transformación adicional de datos
DBeaver >> Administración de base de datos
Notepad++ >> Exploración inicial de archivos

3. Fuentes de Datos

Se utilizaron dos archivos CSV separados por ;:

Tickets

Contiene información de ventas:

punto
ticket
fecha
hora
eancode
ean_desc
unidades_vendidas
precio_regular
precio_promocional
tipo de venta
idcadena
ultmodificacion
anulado
id

Productos

Contiene información del catálogo:

idcadena
eancode
descripcion
sector
seccion
categoría
subcategoría
fabricante
marca
contenido
pesovolumen
unidadmedida
granfamilia
familia
categoria_nueva
subcategoria_nueva
ultmodificacion

Relación definida:

tickets.idcadena = productos.idcadena
AND tickets.eancode = productos.eancode

4. Pipeline de Datos

4.1 Extracción (Python)
Lectura de CSV con pandas
Separador ;
Manejo de encoding (utf-8 / latin1)

🔹 4.2 Transformación

Se aplicaron las siguientes reglas:

Limpieza de nombres de columnas (remoción de comillas)

df_tickets.columns = df_tickets.columns.str.replace('"', '')

Conversión de tipos de datos:
booleanos
texto
fechas
Corrección de errores de codificación

df_tickets = pd.read_csv(
    input_tickets_file,
    sep=";",
    encoding="utf-8", # por los caracteres raros
    dtype={"ticket": "string"},
    true_values=["true"],
    false_values=["false"]
)

4.3 Carga (PostgreSQL)

Creación de tablas relacionales
Inserción masiva con to_sql

df_tickets.to_sql(
    "tickets",
    engine,
    if_exists="append",
    index=False
)

Uso de tipos adecuados:

int
numeric
varchar
date
boolean
time
text
timestamp

5. Análisis de Calidad de Datos

Se identificaron los siguientes problemas:

Valores nulos

En campos como:

contenido
pesovolumen
subcategorías

Problemas de codificación

Caracteres corruptos:

Mercancía → Mercanc�...

Tipos de datos inconsistentes

Columnas con tipos mixtos (ej: texto + numérico)

6. Consultas SQL Desarrolladas

6.1 Creación de la tabla ticket

CREATE TABLE tickets (
	id int8 NOT NULL,
	punto int4 NULL,
	ticket varchar(50) NULL,
	fecha date NULL,
	hora time NULL,
	eancode varchar(50) NULL,
	ean_desc text NULL,
	unidades_vendidas numeric NULL,
	precio_regular numeric(10, 2) NULL,
	precio_promocional numeric(10, 2) NULL,
	tipo_venta varchar(5) NULL,
	idcadena int4 NULL,
	ultmodificacion timestamp NULL,
	anulado bool NULL,
	CONSTRAINT tickets_pkey PRIMARY KEY (id)
);

6.2 Creación de la tabla productos

CREATE TABLE productos (
	id_productos int8 NOT NULL GENERATED ALWAYS AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 1 CACHE 1 NO CYCLE),
	idcadena int4 NULL,
	eancode varchar(50) NULL,
	descripcion text NULL,
	sector text NULL,
	seccion text NULL,
	categoria text NULL,
	subcategoria text NULL,
	fabricante text NULL,
	marca text NULL,
	contenido text NULL,
	pesovolumen text NULL,
	unidadmedida varchar(20) NULL,
	granfamilia text NULL,
	familia text NULL,
	categoria_nueva text NULL,
	subcategoria_nueva text NULL,
	ultmodificacion timestamp NULL,
	CONSTRAINT productos_pkey PRIMARY KEY (id_productos)
);

6.3 Creación de la vista que une la tabla tickets y productos evitando duplicado de filas

Objetivo

Unificar tickets + productos en una tabla de hechos limpia, evitando duplicados y lista para análisis.

Decisiones técnicas

Uso de LEFT JOIN
Permite mantener todas las ventas aunque no exista producto asociado.
Evita pérdida de información en el análisis.

Uso de DISTINCT ON (idcadena, eancode)
Problema: productos tenía múltiples versiones por cambios (ultmodificacion)
Solución: seleccionar una sola versión por producto
Beneficio: evita duplicación de ventas al hacer JOIN

Uso de ORDER BY idcadena, eancode DESC
Ordena registros más de forma descendente

Uso de COALESCE(precio_regular, precio_promocional)
Problema: precios nulos en una de las columnas
Solución: unificar precio en un solo campo
Beneficio: evita pérdida de ventas por valores NULL

Cálculo de métrica derivada (venta)
unidades_vendidas * precio >> Evita recalcular en Power BI y mejora rendimiento del dashboard

Uso de EXTRACT() >> Genera dimensiones de tiempo directamente en SQL: (año, mes, día, trimestre)
Reduce carga en Power BI.

WHERE t.anulado IS NOT TRUE
Descarta ventas anuladas.

create view venta_ticket as
    SELECT 
        t.idcadena,
        t.eancode,
        t.fecha,
        EXTRACT(YEAR FROM t.fecha) AS año,
        EXTRACT(MONTH FROM t.fecha) AS mes,
        EXTRACT(DAY FROM t.fecha) AS dia,
        EXTRACT(QUARTER FROM t.fecha) AS trimestre,
        t.unidades_vendidas,
        COALESCE(t.precio_regular, t.precio_promocional) AS precio,
        t.unidades_vendidas * COALESCE(t.precio_regular, t.precio_promocional) AS venta,       
        p.descripcion,
        p.categoria,
        p.subcategoria,
        p.categoria_nueva,
        p.subcategoria_nueva
    FROM tickets t
	LEFT JOIN (
    	SELECT DISTINCT ON (idcadena, eancode) *
    	FROM productos p
    	ORDER BY idcadena, eancode DESC  -- Prioriza el registro más reciente 
	) p ON t.idcadena = p.idcadena AND t.eancode = p.eancode 
    WHERE t.anulado IS NOT true;

6.4 Creación de la vista que identifica las ventas totales por cadena y trimestre + realiza la comparación del desempeño del primer trimestre de 2023 versus el primer trimestre de 2024

Objetivo

Analizar evolución de ventas y comparar desempeño entre años

Decisiones técnicas

Uso de CTE (WITH ventas_base)
Reutiliza lógica de cálculo de ventas
Mejora legibilidad y mantenimiento

Agregación con SUM()
Calcula ventas totales por:
cadena
año
trimestre

Uso de ROUND()
Controla precisión numérica
Evita problemas de decimales en BI

Uso de función ventana LAG()
LAG(SUM(venta)) OVER (PARTITION BY idcadena, trimestre ORDER BY año)
Permite comparar contra el año anterior.

create view ventas_totales_año_trimestre_cadena_desempeño as
WITH ventas_base AS (
    SELECT 
        t.idcadena,
        t.eancode,
        t.fecha,
        EXTRACT(YEAR FROM t.fecha) AS año,
        EXTRACT(QUARTER FROM t.fecha) AS trimestre,
        t.unidades_vendidas,
        COALESCE(t.precio_regular, t.precio_promocional) AS precio,
        t.unidades_vendidas * COALESCE(t.precio_regular, t.precio_promocional) AS venta,       
        p.descripcion,
        p.categoria,
        p.subcategoria,
        p.categoria_nueva,
        p.subcategoria_nueva
    FROM tickets t
	LEFT JOIN (
    	SELECT DISTINCT ON (idcadena, eancode) *
    	FROM productos p
    	ORDER BY idcadena, eancode DESC  -- Prioriza el registro más reciente
	) p ON t.idcadena = p.idcadena AND t.eancode = p.eancode 
    WHERE t.anulado IS NOT TRUE
	)SELECT 
    	idcadena,
    	año,
    	trimestre,
    	SUM(round(venta::numeric,2)) AS ventas_totales,
    	SUM(round(venta::numeric,2)) - LAG(SUM(venta::numeric)) OVER (PARTITION BY idcadena, trimestre ORDER BY año) AS comparacion
FROM ventas_base
GROUP BY idcadena, año, trimestre
ORDER BY idcadena, año, trimestre;

6.5 Creación de la vista que identifica los 5 productos con mayor venta por cadena

Objetivo

Identificar productos más vendidos por cadena

Decisiones técnicas

Uso de COALESCE(p.descripcion, t.ean_desc)
Obtiene descripción incluso si falta en productos

Uso de RANK()
RANK() OVER (PARTITION BY idcadena ORDER BY SUM(venta) DESC)
Ranking por cadena
Permite análisis interno

Filtro Top 5
WHERE ranking <= 5
Se obtiene el valor deseado del ranking
Reduce volumen en Power BI

create view venta_total_cadena as
WITH ventas_base AS (
    SELECT 
        t.idcadena,
        t.eancode,
        t.fecha,
        EXTRACT(YEAR FROM t.fecha) AS año,
        EXTRACT(MONTH FROM t.fecha) AS mes,
        EXTRACT(QUARTER FROM t.fecha) AS trimestre,
        t.unidades_vendidas,
        COALESCE(t.precio_regular, t.precio_promocional) AS precio,
        t.unidades_vendidas * COALESCE(t.precio_regular, t.precio_promocional) AS venta,       
        coalesce(p.descripcion, t.ean_desc) as descripcion,
        p.categoria,
        p.subcategoria,
        p.categoria_nueva,
        p.subcategoria_nueva
    FROM tickets t
	LEFT JOIN (
    	SELECT DISTINCT ON (idcadena, eancode) *
    	FROM productos p
    	ORDER BY idcadena, eancode DESC  -- Prioriza el registro más reciente
	) p ON t.idcadena = p.idcadena AND t.eancode = p.eancode 
    WHERE t.anulado IS NOT TRUE
)SELECT *
FROM (
    SELECT 
    	año,
    	mes,
        idcadena,
        eancode,
        descripcion,
        SUM(round(venta::numeric,2)) AS total_venta,
        RANK() OVER (PARTITION BY idcadena ORDER BY SUM(venta) DESC) AS ranking
    FROM ventas_base
    GROUP BY año, mes, idcadena, eancode, descripcion
) t
WHERE ranking <= 5;

6.6 Creación de la vista que identifica las 5 categorías con mayor facturación y su contribución porcentual.

Objetivo

Analizar categorías con mayor facturación y contribución porcentual

Decisiones técnicas

Corrección de encoding
convert_from(convert_to(categoria, 'LATIN1'), 'UTF8')
Soluciona caracteres corruptos
Mejora calidad visual en BI

Cálculo de facturación
SUM(venta)
Cálculo de IVA con CASE
CASE 
  WHEN categoria IN (...) THEN SUM(venta) / 21
  ...
END
Simulación de reglas fiscales

Uso de RANK()
Ranking de categorías por facturación
Top 5 categorías por cadena y por periodo
WHERE ranking <= 10

create view venta_total_facturacion as
WITH ventas_base AS (
    SELECT 
        t.idcadena,
        t.eancode,
        t.fecha,
        EXTRACT(YEAR FROM t.fecha) AS año,
        EXTRACT(QUARTER FROM t.fecha) AS trimestre,
        t.unidades_vendidas,
        COALESCE(t.precio_regular, t.precio_promocional) AS precio,
        t.unidades_vendidas * COALESCE(t.precio_regular, t.precio_promocional) AS venta,       
        p.descripcion,
        p.categoria,
        p.subcategoria,
        p.categoria_nueva,
        p.subcategoria_nueva
    FROM tickets t
	LEFT JOIN (
    	SELECT DISTINCT ON (idcadena, eancode) *
    	FROM productos p
    	ORDER BY idcadena, eancode DESC  -- Prioriza el registro más reciente
	) p ON t.idcadena = p.idcadena AND t.eancode = p.eancode 
    WHERE t.anulado IS NOT TRUE
)SELECT *
FROM (
    SELECT 
        idcadena,
   		año,
   		trimestre,
        convert_from(convert_to(categoria, 'LATIN1'), 'UTF8') AS categoria,
        SUM(round(venta::numeric,2)) AS facturacion,
        round(    
        	CASE 
            WHEN categoria IN ('Carniceria', 'Avicola', 'VACUNA XKG') THEN SUM(venta) / 21
            WHEN categoria IN ('Panaderia/ConfiterÃ­a (SOFIPAN)', 'CERVEZAS', 'MASAS PRODUCCION') THEN SUM(venta) / 11
            WHEN categoria IN ('Verduras', 'LEGUMBRES X KG') THEN 0  -- Exentas
            ELSE 0
        	end, 2) AS iva,
        rank() OVER (PARTITION BY idcadena ORDER BY SUM(venta) DESC) AS ranking
    FROM ventas_base
    GROUP BY idcadena, año, trimestre, categoria
) t
WHERE ranking <= 10;

6.7 Creación de la vista para evaluar el desempeño por categorías y familias de productos en Power BI

Objetivo

Analizar jerarquía (familia >> categoría).

Decisiones técnicas

Uso de COALESCE(familia, granfamilia)
Problema: datos incompletos.
Solución: obtiene datos de la segunda columna si falta en la primera
Beneficio: evita valores NULL en análisis

Modelo jerárquico
Permite análisis en Power BI

create view venta_categoria_familia as
WITH ventas_base AS (
    SELECT 
        t.idcadena,
        t.eancode,
        t.fecha,
        EXTRACT(YEAR FROM t.fecha) AS año,
        EXTRACT(QUARTER FROM t.fecha) AS trimestre,
        t.unidades_vendidas,
        COALESCE(t.precio_regular, t.precio_promocional) AS precio,
        t.unidades_vendidas * COALESCE(t.precio_regular, t.precio_promocional) AS venta,       
        p.descripcion,
        coalesce(p.familia, p.granfamilia) as familia,
        p.categoria,
        p.subcategoria,
        p.categoria_nueva,
        p.subcategoria_nueva
    FROM tickets t
	LEFT JOIN (
    	SELECT DISTINCT ON (idcadena, eancode) *
    	FROM productos p
    	ORDER BY idcadena, eancode DESC  -- Prioriza el registro más reciente
	) p ON t.idcadena = p.idcadena AND t.eancode = p.eancode 
    WHERE t.anulado IS NOT TRUE
)SELECT *
FROM (
    SELECT 
        idcadena,
   		año,
   		trimestre,
   		familia,
        convert_from(convert_to(categoria, 'LATIN1'), 'UTF8') AS categoria,
        SUM(round(venta::numeric,2)) AS facturacion,
        round(    
        	CASE 
            WHEN categoria IN ('Carniceria', 'Avicola', 'VACUNA XKG') THEN SUM(venta) / 21
            WHEN categoria IN ('Panaderia/ConfiterÃ­a (SOFIPAN)', 'CERVEZAS', 'MASAS PRODUCCION') THEN SUM(venta) / 11
            WHEN categoria IN ('Verduras', 'LEGUMBRES X KG') THEN 0  -- Exentas
            ELSE 0
        	end, 2) AS iva,
        rank() OVER (PARTITION BY idcadena ORDER BY SUM(venta) DESC) AS ranking
    FROM ventas_base
    GROUP BY idcadena, 
    año, trimestre, familia, categoria
) t
WHERE ranking <= 10
order by año asc;

7. Modelado en Power BI

Modelo de datos

Tabla de hechos: vw_venta_ticket

Contiene el detalle de todas las transacciones de venta.
Incluye información de tickets y atributos de productos.

Tabla de dimensiones: Calendario

Tabla Calendario creada con DAX

Tabla de fechas creada en DAX.
Permite análisis por año, mes, trimestre y día.

Calendario = 
ADDCOLUMNS(
    CALENDAR(DATE(2023,1,1), DATE(2024,12,31)),
    "Año", YEAR([Date]),
    "Mes Numero", MONTH([Date]),
    "Mes", FORMAT([Date], "MMMM"),
    "Mes Corto", FORMAT([Date], "MMM"),
    "Año-Mes", FORMAT([Date], "YYYY-MM"),
    "Trimestre", "T" & FORMAT([Date], "Q"),
    "Dia", DAY([Date]),
    "Dia Semana", FORMAT([Date], "dddd"),
    "Dia Semana Num", WEEKDAY([Date], 2),
    "AñoMesOrden", YEAR([Date]) * 100 + MONTH([Date])
)

Tablas agregadas (vistas SQL)

Se crearon múltiples vistas en PostgreSQL con el objetivo de mejorar el rendimiento y facilitar el análisis

vw_ventas_totales_año_trimestre_cadena_desempeño
vw_venta_total_cadena
vw_venta_total_facturacion
vw_venta_categoria_familia

8. Dashboard en Power BI

Visualizaciones implementadas:

imagen >> Inicio del Dashboard
navegador de páginas >> Inicio del dashboard / Página General / Página Productos & Categorías / Página Comparación de Cadenas
Gráfico de barras >> Venta anual por cadena / Productos más vendidos
Gráfico de columnas >> Días con mayor volumen de ventas / Desempeño por categorías y familias de productos
Gráfico circular / anillo >> Venta total por cadenas / Mayor Contribución Por Categoría
Tabla >> Top 5 Productos Con Mayor Venta / Facturación Por Categoría / Contribución Por Categoría
Gráfico temporal >> Ventas por día
Segmentadores >> Cadena / Periodo / Categoría / Mes / Trimestre

Lenguaje M utilizado para eliminar una columna de la tabla vw_venta_categoria_familia

= Table.RemoveColumns(public_venta_categoria_familia,{"ranking"})

Lenguaje M utilizado para reemplazar valores nulos a "A DEFINIR" dentro de las columnas familia y categoria en la tabla vw_venta_categoria_familia

= Table.ReplaceValue(#"Columnas quitadas",null,"A DEFINIR",Replacer.ReplaceValue,{"familia", "categoria"})

Medida DAX utilizada para obtener el costo por cada venta en la tabla de hechos vw_venta_ticket

med_venta_total_por_ticket = SUMX(vw_venta_ticket, vw_venta_ticket[unidades_vendidas] * vw_venta_ticket[precio])


9. Insights

Diferencias de desempeño entre cadenas
Determinados productos concentran gran parte de las ventas
Algunas categorías tienen una contribución desproporcionada a la facturación total
Se detectaron picos de ventas en días específicos, posiblemente asociados a fines de semana o promociones

10. Conclusión

Este proyecto demuestra la capacidad de:

Construir un pipeline completo de datos
Resolver problemas de calidad de datos
Diseñar modelos analíticos
Crear dashboards interactivos
Comunicar insights de negocio de forma clara

11. Posibles Mejoras

Implementar ETL automatizado
Crear Data Warehouse
Optimizar consultas SQL

12. Autor

Mauricio Figueredo
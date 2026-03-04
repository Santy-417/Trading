# NextFlow TradingAI — Guía de la Plataforma

> **Versión:** 2.0 | **Actualizado:** Marzo 2026
> **Stack:** FastAPI backend · Next.js 14 frontend · MetaTrader 5 · XGBoost · GPT-4o-mini

---

## Tabla de Contenidos

1. [Inicio de Sesión](#1-inicio-de-sesión)
2. [Dashboard — Trading](#2-dashboard--trading)
3. [Backtest](#3-backtest)
4. [Modelos ML](#4-modelos-ml)
5. [Análisis IA](#5-análisis-ia)
6. [Gestión de Riesgo](#6-gestión-de-riesgo)
7. [Registro de Auditoría](#7-registro-de-auditoría)
8. [Configuración](#8-configuración)
9. [Guía de Interpretación de Métricas](#9-guía-de-interpretación-de-métricas)
10. [Solución de Problemas](#10-solución-de-problemas)

---

## 1. Inicio de Sesión

### Cómo acceder
- Abre `http://localhost:3000` — redirige automáticamente a `/login` si no estás autenticado
- La autenticación se gestiona mediante **Supabase** (correo + contraseña)

### Indicador de estado del sistema
- **"Sistema en Línea" (verde)** — El backend FastAPI en `localhost:8000` está respondiendo correctamente
- **"Sistema Fuera de Línea" (amarillo)** — El backend no está corriendo; iniciarlo con `uvicorn app.main:app --reload --port 8000`

### Modo desarrollo
- Con `NODE_ENV=development`, la autenticación se omite usando un token de desarrollo (`dev-bypass-token`)
- En producción se requiere un JWT válido de Supabase

---

## 2. Dashboard — Trading

### Descripción general
Página principal de operación en vivo. Controla el bot, ejecuta órdenes manuales y muestra posiciones abiertas en tiempo real.

### Control del Bot

| Botón | Acción |
|-------|--------|
| **Iniciar** | Arranca el bot de trading automatizado sobre el símbolo seleccionado |
| **Detener** | Detiene el bot de forma ordenada (no abre nuevas operaciones, las posiciones abiertas continúan) |
| **Kill Switch** | Parada de emergencia — cierra TODAS las posiciones abiertas de inmediato y detiene el bot |

> **Advertencia:** El Kill Switch no se puede deshacer. Todas las posiciones se cierran al precio de mercado actual.

### Selección de Símbolo
- 9 pares soportados: `EURUSD`, `XAUUSD`, `DXY`, `USDCAD`, `GBPUSD`, `AUDCAD`, `EURJPY`, `USDJPY`, `EURGBP`
- Cambiar el símbolo actualiza el gráfico TradingView y la cabecera de contexto
- La cabecera muestra el P&L actual del símbolo activo

### Operación Manual
- **Símbolo / Dirección (BUY·SELL) / Tamaño de lote** — todos obligatorios
- **Stop Loss / Take Profit** — opcionales, en pips
- La operación pasa por el motor de riesgo antes de ejecutarse (circuit breaker, kill switch, límite de pérdida diaria)
- Las operaciones rechazadas muestran la regla específica que bloqueó la ejecución

### Tabla de Posiciones
- Muestra todas las posiciones abiertas actualmente en MT5
- Columnas: Ticket, Símbolo, Tipo, Volumen, Precio de Entrada, Precio Actual, P&L
- Se actualiza automáticamente cada 10 segundos

### Widget TradingView
- Gráfico en vivo integrado para el símbolo seleccionado
- Soporta todas las funciones estándar de TradingView (indicadores, trazados, cambio de temporalidad)

### Indicador de Sesión (Cabecera)
- Muestra la sesión de trading activa: **Asiática**, **Londres** o **Nueva York**
- Basado en la hora UTC convertida a zona horaria de Bogotá (UTC-5)

---

## 3. Backtest

### Descripción general
Simula una estrategia de trading sobre datos históricos de MT5 sin ejecutar operaciones reales.

### Configuración

#### Estrategia y Mercado
| Parámetro | Opciones | Notas |
|-----------|---------|-------|
| **Estrategia** | Fibonacci, ICT, Hybrid ML, Bias (SMC+ML) | Bias es la estrategia más optimizada |
| **Símbolo** | 9 pares forex | EURUSD H1 es el más probado |
| **Temporalidad** | M5, M15, H1, H4, D1 | H1 recomendado para la estrategia Bias |

#### Rango de Datos — dos modos

**Modo Cantidad de Velas** (por defecto)
- Define el número de velas históricas a cargar (100 – 50.000)
- Más simple; siempre carga las N velas más recientes desde MT5

**Modo Rango de Fechas** (interruptor)
- Define **Fecha de Inicio** y **Fecha de Fin**
- **Velas de Calentamiento** (50–500, por defecto 200) — velas cargadas *antes* de la fecha de inicio para pre-calcular indicadores (RSI, MACD, EMA, entropía, sesgo diario). Estas velas no se operan.
- Un **banner de estimación** muestra el total aproximado de velas que se cargarán

#### Configuración de Riesgo
| Parámetro | Rango | Por Defecto | Notas |
|-----------|-------|------------|-------|
| **Balance Inicial** | ≥ $100 | $10.000 | Capital inicial para la simulación de P&L |
| **Riesgo por Operación** | 0,1% – 5,0% | 1,0% | Porcentaje del balance arriesgado por operación |
| **Modo de Lote** | percent_risk | percent_risk | El tamaño de lote se calcula automáticamente según el riesgo % |

### Resultados

#### Métricas Principales
| Métrica | Bueno | Precaución | Peligro |
|---------|-------|------------|---------|
| **Ganancia Neta** | Positiva | — | Negativa |
| **Tasa de Éxito** | ≥ 50% | 40–50% | < 40% |
| **Factor de Beneficio** | ≥ 1,5 | 1,0–1,5 | < 1,0 |

#### Métricas de Rendimiento
| Métrica | Descripción | Rango ideal |
|---------|-------------|-------------|
| **Sharpe Ratio** | Retorno ajustado por riesgo vs volatilidad | > 1,0 |
| **Sortino Ratio** | Como Sharpe pero solo penaliza la volatilidad negativa | > 1,0 |
| **Calmar Ratio** | Retorno anual / drawdown máximo | > 1,0 |
| **Drawdown Máx. %** | Mayor caída desde el pico de la curva de equity | < 10% |
| **VaR 95%** | Value at Risk: peor pérdida diaria esperada el 95% del tiempo | Depende del contexto |
| **CVaR 95%** | VaR Condicional: pérdida media en el peor 5% de los días | Depende del contexto |
| **Ganancia Media / Pérdida Media** | Tamaño promedio de operaciones ganadoras y perdedoras | Ganancia > Pérdida |

#### Distribución BUY/SELL
- Muestra cuántas operaciones fueron BUY vs SELL
- Un gran desequilibrio (ej. 90% SELL) puede indicar un bug o sesgo de mercado
- Para la estrategia Bias, cierto desequilibrio es esperado según el período analizado

#### Análisis por Sesión
- Desglosa el P&L por sesión (Londres vs Nueva York)
- Útil para ver en qué sesión la estrategia rinde mejor

#### Curva de Equity
- Representación visual del balance a lo largo del tiempo
- **Línea de referencia punteada** = balance inicial
- El tooltip muestra: valor de equity, P&L desde el inicio y drawdown en ese punto
- El chip de retorno % en la esquina superior derecha muestra el retorno total

#### Modo Comparación
1. Ejecuta un primer backtest (Período A) — los resultados aparecen en el panel derecho
2. Activa el interruptor **Comparar Períodos** en el panel izquierdo
3. Ajusta fechas/velas para el Período B y haz clic en **Ejecutar Período B**
4. Aparecen tres pestañas: **Período A | Período B | Comparación**
5. La pestaña Comparación muestra valores delta (positivo = Período B mejoró)

### Exportar Resultados del Backtest

Tras completar un backtest, aparecen dos botones de exportación:

- **Copiar Reporte** (icono portapapeles) — genera un reporte Markdown estructurado con todas las métricas, lista de operaciones y datos por sesión. Listo para pegar en Claude, ChatGPT o cualquier IA para análisis de estrategia.
- **Exportar JSON** (icono descarga) — descarga un archivo `.json` con el resultado completo incluyendo curva de equity y operaciones individuales.

---

## 4. Modelos ML

### Descripción general
Entrena clasificadores XGBoost sobre datos históricos de precios para predecir la dirección de la operación (BUY/SELL/NEUTRAL). Los modelos se usan como filtros en las estrategias Hybrid ML y Bias.

### Configuración del Entrenamiento

#### Configuración del Modelo
| Parámetro | Opciones | Notas |
|-----------|---------|-------|
| **Símbolo** | 8 pares (sin DXY) | Usar el mismo símbolo que operas |
| **Temporalidad** | M5, M15, H1, H4, D1 | H1 recomendado |

#### Datos de Entrenamiento — dos modos

**Modo Cantidad de Velas** (por defecto)
- **Velas Históricas**: 500 – 50.000 (por defecto: 5.000)
- Más velas = más datos de entrenamiento pero más lento

**Modo Rango de Fechas** (interruptor)
- **Fecha de Inicio / Fecha de Fin** — carga una ventana histórica específica
- **Velas de Calentamiento** (50–500, por defecto 200) — velas antes de la fecha de inicio usadas para inicializar indicadores (no incluidas en el dataset de entrenamiento)
- El banner de estimación muestra cuántas velas se cargarán

> **Consejo:** Para entrenar, usa Rango de Fechas para hacer coincidir exactamente el período que backtestaste, así el modelo aprende del mismo régimen de mercado.

### Proceso de Entrenamiento
1. Se cargan datos desde MT5 (cantidad de velas o rango de fechas)
2. La **ingeniería de características** crea ~45 features: RSI, MACD, Bandas de Bollinger, ATR, EMA-20/50/200, momentum, volumen y features SMC (distancia PDH/PDL, detección de sweeps, sesgo de sesión, entropía, niveles de fractal)
3. Se calcula una **etiqueta de retorno futuro**: cada vela se etiqueta como 1 (BUY) si el precio sube en las próximas N velas (por defecto: 10), o 0 (SELL/NEUTRAL) en caso contrario
4. Los datos se dividen 80/20 (entrenamiento/prueba)
5. Se entrena **XGBoost** con preprocesamiento StandardScaler
6. El modelo se guarda en el registro de modelos

### Resultados del Entrenamiento

| Métrica | Descripción | Interpretación |
|---------|-------------|----------------|
| **Accuracy** | % de predicciones correctas en el conjunto de prueba | > 60% es bueno; 100% = probable sobreajuste |
| **Precision** | De los BUY predichos, cuántos fueron correctos | Mayor = menos señales BUY falsas |
| **Recall** | De los BUY reales, cuántos fueron detectados | Mayor = captura más oportunidades BUY |
| **F1 Score** | Media armónica de Precision y Recall | Métrica balanceada |
| **Muestras de Prueba** | Número de velas en el conjunto de prueba | Más muestras = métricas más confiables |
| **Tasa Positiva** | % de etiquetas BUY en los datos de prueba | Cerca de 0,42–0,58 = dataset balanceado |
| **Tasa Positiva Predicha** | % de velas predichas como BUY | Debería estar cerca de la Tasa Positiva |

> **Advertencia:** Un accuracy del 100% casi siempre indica **sobreajuste** o **fuga de datos** — el modelo memorizó los datos de entrenamiento. Esto es común con datasets pequeños o datos muy recientes. Usa validación walk-forward para obtener métricas más honestas.

### Características Principales (Top Features)
- Gráfico de barras con las 10 características más importantes para las predicciones del modelo
- Features con importancia muy alta (> 0,5) como `forward_return` son sospechosas — indica que la etiqueta se filtró a las características
- Un modelo saludable muestra importancia distribuida entre RSI, MACD, EMA y features SMC

### Exportar Resultados del Entrenamiento
- El botón **Exportar JSON** aparece tras el entrenamiento — descarga el ID del modelo, métricas y top features como archivo JSON
- Útil para compartir resultados con una IA para análisis o mantener registros históricos

### Modelos Guardados
- Lista todos los modelos entrenados y persistidos en el registro
- Haz clic en cualquier fila para **expandirla** y ver métricas completas + características principales
- Botón **Exportar JSON** en cada modelo expandido
- Botón **Predecir** (icono rayo): usa el modelo para predecir la señal en las últimas 500 velas del símbolo/temporalidad configurado
- Botón **Eliminar** (icono papelera): eliminación en dos pasos — primer clic pone el botón en rojo, segundo clic elimina definitivamente (se resetea solo en 3 segundos si no confirmas)

### Resultado de Predicción
Tras hacer clic en Predecir:
- Señal **BUY / SELL / NEUTRAL**
- Barra de **Probabilidad** (0–100%) — confianza del modelo en su predicción
- **Nivel de confianza**: Alto (>70%), Medio (50–70%), Bajo (<50%)

> Las predicciones son solo orientativas. El modelo nunca ejecuta operaciones directamente.

### Validación Walk-Forward
- Úsala para validar un modelo guardado con pruebas más realistas fuera de muestra
- Divide los datos en N pliegues ordenados temporalmente (por defecto: 5)
- Cada pliegue: entrena en datos anteriores, prueba en datos posteriores
- Más honesta que una sola división entrenamiento/prueba

---

## 5. Análisis IA

### Descripción general
Usa **GPT-4o-mini** para generar análisis en lenguaje natural de tus datos de trading. El análisis es solo orientativo — la IA nunca ejecuta operaciones.

### Tipos de Análisis

| Tipo | Endpoint | Qué analiza |
|------|----------|-------------|
| **Análisis de Operaciones** | `/ai/analyze-trades` | Patrones en operaciones recientes (tasa de éxito por sesión, hora del día, símbolo) |
| **Rendimiento** | `/ai/performance-summary` | Reporte de rendimiento general (semanal o mensual) |
| **Parámetros** | `/ai/suggest-parameters` | Ajustes sugeridos de parámetros de riesgo basados en datos recientes |
| **Revisión de Riesgo** | `/ai/risk-review` | Eventos de riesgo recientes, activaciones del circuit breaker, anomalías |
| **Comparar** | `/ai/compare-strategies` | Comparación lado a lado de las estrategias Fibonacci, ICT y Hybrid ML |

### Configuración
- **Análisis de Operaciones / Revisión de Riesgo**: Define el número de días hacia atrás (1–90)
- **Rendimiento**: Elige el período (Semanal = últimos 7 días, Mensual = últimos 30 días)
- **Parámetros** y **Comparar**: Sin configuración adicional

### Cómo usar
1. Selecciona un tipo de análisis desde las tarjetas superiores
2. Configura los parámetros en el panel izquierdo
3. Haz clic en **Ejecutar Análisis**
4. Los resultados aparecen en el panel derecho (con scroll, hasta 500px)
5. Usa el botón **Copiar al portapapeles** para guardar o pegar el análisis

### Resultados esperados
- Análisis de Operaciones: Resumen de patrones, mejores/peores sesiones y símbolos, desglose de tasa de éxito
- Rendimiento: Resumen narrativo con métricas clave y observaciones
- Parámetros: Cambios específicos sugeridos al porcentaje de riesgo, tamaño de lote o parámetros de estrategia
- Revisión de Riesgo: Lista de eventos anómalos con explicaciones
- Comparar: Comparación en formato tabla con recomendación de qué estrategia usar

---

## 6. Gestión de Riesgo

### Descripción general
Monitoreo en tiempo real de tres indicadores de riesgo: Drawdown, Pérdida Diaria y Sobreoperación. También muestra una línea de tiempo de eventos de riesgo recientes.

### Indicadores

| Indicador | Qué mide | Umbral |
|-----------|---------|--------|
| **Drawdown** | Caída actual desde el balance máximo | Límite por defecto: 10% |
| **Pérdida Diaria** | P&L total negativo del día | Límite por defecto: 3% del balance |
| **Sobreoperación** | Número de operaciones hoy | Límite por defecto: 10 operaciones |

- El indicador se llena de 0% a 100% conforme te acercas al límite
- Color: Verde (seguro) → Amarillo (precaución, >70%) → Rojo (crítico, >90%)

### Banner de Estado
| Banner | Significado |
|--------|-------------|
| **Trading Activo** (verde) | El bot está corriendo y el trading está permitido |
| **Trading Detenido** (rojo) | El bot está parado O se alcanzó un límite de riesgo — no se abren nuevas operaciones |
| **Backend No Disponible** (amarillo) | El servidor FastAPI no responde — verificar si está corriendo |

> **"Trading Detenido" es normal cuando el bot no está iniciado.** No indica un error.

### Línea de Tiempo de Eventos de Riesgo
- Lista los disparadores recientes de reglas de riesgo: activaciones del circuit breaker, usos del kill switch, alcance del límite de pérdida diaria
- Cada evento muestra timestamp, tipo y descripción

### Panel de Configuración de Riesgo
- Muestra los límites actuales (drawdown %, pérdida diaria %, máximo de operaciones)
- La configuración se define en el `.env` del backend o en la configuración del bot

### Frecuencia de Actualización
- La página consulta el backend cada **5 segundos**
- Cuando el backend no está disponible, muestra "Reintentando..." en lugar de "Actualiza cada 5s"

---

## 7. Registro de Auditoría

### Descripción general
Historial completo de todas las operaciones, con filtros, ordenamiento y capacidades de exportación.

### Fuente de Datos
1. **Principal:** Operaciones almacenadas en la base de datos PostgreSQL de Supabase
2. **Alternativa:** Si la base de datos está vacía, obtiene los datos directamente desde MT5 `history_deals_get()`

### Filtros
- **Fecha Desde / Fecha Hasta** — filtrar operaciones por fecha de ejecución
- **Símbolo** — filtrar por par de trading
- Haz clic en **Aplicar** para actualizar la tabla con los filtros seleccionados

### Columnas de la Tabla
| Columna | Descripción |
|---------|-------------|
| **Ticket** | Número de ticket de orden en MT5 |
| **Símbolo** | Par de trading |
| **Tipo** | BUY o SELL |
| **Volumen** | Tamaño en lotes |
| **Entrada** | Precio de entrada |
| **Cierre** | Precio de cierre |
| **P&L** | Ganancia o pérdida en USD |
| **Hora de Apertura** | Cuándo se abrió la operación |
| **Hora de Cierre** | Cuándo se cerró la operación |

- Haz clic en cualquier **encabezado de columna** para ordenar ascendente/descendente
- Haz clic en cualquier **fila** para abrir un modal de detalle con toda la información de la operación

### Exportar
- Botón **Exportar CSV** — descarga la lista de operaciones filtrada actual como archivo `.csv`
- Útil para análisis externo en Excel, Python o herramientas de reporte

### Paginación
- Muestra 50 operaciones por página (configurable)
- Botones de navegación en la parte inferior

---

## 8. Configuración

### Descripción general
Muestra información de la plataforma y estado de las conexiones.

- Versión de la plataforma
- Estado de conexión con el backend
- Entorno (desarrollo / producción)

---

## 9. Guía de Interpretación de Métricas

### Rendimiento del Backtest

```
Factor de Beneficio = Ganancia Bruta Total / Pérdida Bruta Total

Ejemplo: Factor de Beneficio 1,36 significa que por cada $1 perdido, ganas $1,36
- < 1,0 = estrategia perdedora
- 1,0–1,5 = marginal, necesita mejorar
- > 1,5 = ventaja sólida
- > 2,0 = muy fuerte (verificar que no esté sobre-optimizado)
```

```
Sharpe Ratio = (Retorno - Tasa Libre de Riesgo) / Desviación Estándar de los Retornos

- < 0 = peor que mantener efectivo
- 0–1 = aceptable
- 1–2 = bueno
- > 2 = excelente (verificar con walk-forward)
```

```
Drawdown Máximo = Mayor caída pico a valle en la curva de equity

- < 5% = conservador
- 5–15% = típico para estrategias activas
- > 20% = alto riesgo
```

### Calidad del Modelo ML

```
Accuracy del 100% → Sobreajuste (nunca confiar en esto para trading en vivo)

Rango de accuracy saludable: 55–70% en el conjunto de prueba
Un modelo con 60% de aciertos y buena gestión del riesgo puede ser rentable.
```

```
Tasa Positiva ≈ Tasa Positiva Predicha → El modelo está calibrado (sin sesgo)
Gran diferencia entre ambas → El modelo sobre-predice o infra-predice sistemáticamente una dirección
```

### Usando Resultados de Backtest con IA

Cuando exportas un reporte de backtest y lo pegas en una IA (Claude, ChatGPT):

**Buenos prompts:**
- "Analiza este backtest. ¿Cuáles son las principales debilidades y cómo ajustarías los parámetros de riesgo?"
- "Según el análisis de sesiones, ¿debería operar solo en sesión Londres o Nueva York?"
- "La distribución BUY/SELL es 82% SELL. ¿Es un bug o una perspectiva válida del mercado?"
- "Compara el Período A vs Período B. ¿Qué cambió y por qué difirió el rendimiento?"

**En qué puede ayudar la IA:**
- Identificar patrones en la lista de operaciones (pérdidas repetidas en ciertos horarios)
- Sugerir ajustes de parámetros (SL más ajustado, diferente ratio RR)
- Explicar valores de métricas en contexto
- Comparar rendimiento de estrategias entre períodos

**Qué no puede hacer la IA:**
- Acceder a tu cuenta MT5 o datos en vivo
- Ejecutar cambios automáticamente
- Garantizar rendimiento futuro

---

## 10. Solución de Problemas

### "Sistema Fuera de Línea" en la página de login
- El backend no está corriendo → `cd backend && uvicorn app.main:app --reload --port 8000`

### "Trading Detenido" en la página de Riesgo
- Es normal cuando el bot no está iniciado
- Inicia el bot desde la página de Trading

### "Backend No Disponible" (amarillo) en la página de Riesgo
- FastAPI no responde → revisa el terminal del backend para ver errores

### El entrenamiento ML devuelve 100% de accuracy
- El dataset es muy pequeño o muy reciente → usa más velas o un rango de fechas más amplio
- Fuga de características → verifica si `forward_return` aparece en las top features con importancia muy alta (> 0,5)
- Normal para datos muy recientes donde el patrón era muy claro

### El backtest devuelve 0 operaciones
- La estrategia no encontró señales válidas en el período/símbolo seleccionado
- Prueba: rango de fechas más largo, diferente temporalidad, diferente símbolo
- Verifica que MT5 esté conectado y tenga datos para el par seleccionado

### El Análisis IA devuelve "Error de Red"
- La clave de la API de OpenAI no está configurada en `.env` → agrega `OPENAI_API_KEY=sk-...`
- Revisa los logs del backend para ver errores de API

### MT5 no conectado
- MetaTrader 5 debe estar corriendo en la misma máquina que el backend
- Verifica que el terminal MT5 esté conectado con una cuenta válida
- El backend no podrá cargar datos históricos si MT5 no está conectado

### Errores de conexión con Supabase
- Verifica `SUPABASE_URL` y `SUPABASE_KEY` en el `.env` del backend
- Verifica `NEXT_PUBLIC_SUPABASE_URL` y `NEXT_PUBLIC_SUPABASE_ANON_KEY` en el `.env.local` del frontend

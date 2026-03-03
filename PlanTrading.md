# Plan de Trading - BiasStrategy V1 (Smart Money Concepts)

**Trader:** Santiago
**Plataforma:** MetaTrader 5 (Automatizado)
**Metodología:** Smart Money Concepts (SMC) V1
**Versión:** 1.0 - Marzo 2026
**Estado:** Producción (validado con datos reales MT5)

---

## 1. Resumen Ejecutivo

| Campo | Detalle |
|-------|---------|
| **Mercado** | Forex (Divisas) |
| **Instrumento Principal** | EURUSD |
| **Timeframe Operativo** | H1 (optimizado y validado) |
| **Timeframe de Confirmación** | M5 (ChoCh y Fractal Break) |
| **Timeframe de Bias** | D1 (sesgo direccional diario) |
| **Estilo** | Intraday / Swing corto |
| **Sesiones** | London (manipulación) → New York (entrada) |
| **Riesgo por Trade** | 1.0% del balance (ajustable por ML: 0.5%-1.5%) |
| **Risk-Reward Mínimo** | 1.3:1 |
| **Objetivo Mensual** | 5-10% de retorno neto |
| **Drawdown Máximo Permitido** | 10% (circuit breaker automático) |
| **Pérdida Diaria Máxima** | 3% (circuit breaker automático) |

---

## 2. Filosofía de Trading

### Enfoque Institucional (Smart Money Concepts)

Este plan se basa en la premisa de que los mercados son movidos por participantes institucionales (bancos, fondos de cobertura, market makers) que necesitan liquidez para ejecutar órdenes grandes. La estrategia identifica:

1. **Manipulación de Liquidez:** Las instituciones empujan el precio hacia zonas de stop-loss (PDH/PDL) para capturar liquidez antes de mover el precio en la dirección real.

2. **Sesgo Diario (Daily Bias):** La vela D1 anterior indica la intención direccional del mercado para el día actual.

3. **Confirmación Estructural:** Después de la manipulación, se busca un cambio de carácter (ChoCh) o ruptura fractal que confirme la reversión.

### Principios Fundamentales

- **No perseguir el precio:** Solo entrar después de manipulación confirmada.
- **La liquidez precede al movimiento:** Sweeps de PDH/PDL son señales, no ruido.
- **Confluencia temporal:** London manipula, New York ejecuta.
- **Datos sobre emociones:** Todas las decisiones están automatizadas y basadas en reglas cuantificables.

---

## 3. Instrumentos y Mercados

### Pares Soportados

| Par | Tipo | Spread | Comisión | Slippage | Pip Value | Point |
|-----|------|--------|----------|----------|-----------|-------|
| **EURUSD** | Major (Principal) | 1.2 pips | $7.0/lote | 0.3 pips | $10.0/pip | 0.0001 |
| **XAUUSD** | Commodity | 3.0 pips | $7.0/lote | 1.0 pip | $1.0/pip | 0.01 |
| GBPUSD | Major | Variable | $7.0/lote | Variable | $10.0/pip | 0.0001 |
| USDCAD | Major | Variable | $7.0/lote | Variable | Variable | 0.0001 |
| EURJPY | Cross | Variable | $7.0/lote | Variable | Variable | 0.01 |
| USDJPY | Major | Variable | $7.0/lote | Variable | Variable | 0.01 |
| EURGBP | Cross | Variable | $7.0/lote | Variable | Variable | 0.0001 |
| AUDCAD | Cross | Variable | $7.0/lote | Variable | Variable | 0.0001 |
| DXY | Index | Variable | $7.0/lote | Variable | Variable | 0.001 |

> **Nota:** EURUSD H1 es el par principal optimizado y validado. Otros pares requieren re-optimización de parámetros antes de operar en producción.

---

## 4. Horarios de Trading

### Sesiones Operativas (Hora Colombia / Bogotá, UTC-5)

```
02:00 ─────── LONDON SESSION (Manipulación) ─────── 11:30
                    Detección de sweeps PDH/PDL
                    Manipulación se almacena para NY

08:00 ─────── NY SESSION (Entrada) ─────── 14:00
                    Confirmación ChoCh / Fractal Break
                    Ejecución de trades

14:00 ─────── EXTENDED ENTRY ─────── 18:00
                    Solo si manipulación persistente de London
                    (sweep detectado pero sin entrada en NY regular)

16:30 ─────── TIME-BASED CLOSE ─────── (21:30 UTC)
                    Cierre automático de todas las posiciones abiertas
                    Reset de señales al cierre del día
```

### Conversión a UTC

| Evento | Bogotá (UTC-5) | UTC |
|--------|----------------|-----|
| London Start | 02:00 | 07:00 |
| London End | 11:30 | 16:30 |
| NY Start | 08:00 | 13:00 |
| NY End | 14:00 | 19:00 |
| Extended End | 18:00 | 23:00 |
| Time Close | 16:30 | 21:30 |

### Filtro de Noticias

**Ventana de exclusión:** ±5 minutos alrededor de eventos High Impact.

No se ejecutan trades si hay un evento de alto impacto programado dentro de los próximos 5 minutos, ni se aceptan señales si un evento ocurrió hace menos de 5 minutos.

**Eventos monitoreados:**
- Non-Farm Payrolls (NFP) - USD
- Consumer Price Index (CPI) - USD
- FOMC Rate Decision + Press Conference - USD
- ECB Rate Decision + Press Conference - EUR
- BOE Rate Decision - GBP
- GDP (Final) - USD
- Unemployment Rate - USD

**Mapeo de divisas por par:**

| Par | Divisas afectadas |
|-----|-------------------|
| EURUSD | EUR, USD |
| XAUUSD | XAU, USD |
| GBPUSD | GBP, USD |
| USDCAD | USD, CAD |
| EURJPY | EUR, JPY |
| USDJPY | USD, JPY |
| EURGBP | EUR, GBP |
| AUDCAD | AUD, CAD |
| DXY | USD |

---

## 5. Reglas de Entrada (Setup Completo)

### Flujo de Señal

```
D1 Candle (Bias)
    │
    ▼
┌─────────────────────┐
│  PASO 1: Daily Bias │
│  Bullish / Bearish  │
│  / Neutral (Doji)   │
└────────┬────────────┘
         │
         ▼
┌─────────────────────────────┐
│  PASO 2: London Manipulation │
│  PDH/PDL Sweep Detection     │
│  (02:00-11:30 Bogotá)        │
└────────┬────────────────────┘
         │ Sweep confirmado
         ▼
┌─────────────────────────────────┐
│  PASO 3: NY Session Confirmation │
│  ChoCh Híbrido  ──o──  Fractal  │
│  (08:00-14:00 Bogotá)    Break   │
└────────┬────────────────────────┘
         │ Estructura confirmada
         ▼
┌──────────────────────────┐
│  PASO 4: Filtro Entropía │
│  Shannon H < 3.1         │
└────────┬─────────────────┘
         │ Mercado con régimen definido
         ▼
┌──────────────────────────┐
│  PASO 5: Filtro ML       │
│  Confidence > 0.65       │
│  (si modelo cargado)     │
└────────┬─────────────────┘
         │
         ▼
    EJECUTAR TRADE
```

---

### PASO 1: Daily Bias (Sesgo Diario)

Se analiza la vela D1 del día anterior para determinar la dirección probable del día actual.

| Condición | Bias | Acción |
|-----------|------|--------|
| Close > Open (vela alcista) | **BULLISH** | Solo buscar BUY |
| Close < Open (vela bajista) | **BEARISH** | Solo buscar SELL |
| Body < 20% del rango total (Doji) | **NEUTRAL** | Buscar sweeps en AMBAS direcciones |

**Detección de Doji:** Si el cuerpo de la vela D1 es menor al 20% del rango High-Low, se considera indecisión. En este caso, el sistema busca manipulación en ambas direcciones.

---

### PASO 2: London Manipulation (Sweep de PDH/PDL)

Durante la sesión de London (02:00-11:30 Bogotá), el sistema detecta sweeps del Previous Day High (PDH) o Previous Day Low (PDL).

**Sweep Alcista (Bullish - para BUY):**
- Precio Low < PDL + tolerancia (3.0 pips)
- Close retorna por encima del PDL dentro de las siguientes 3 velas
- Indica: instituciones capturaron liquidez de stop-loss de vendedores

**Sweep Bajista (Bearish - para SELL):**
- Precio High > PDH - tolerancia (3.0 pips)
- Close retorna por debajo del PDH dentro de las siguientes 3 velas
- Indica: instituciones capturaron liquidez de stop-loss de compradores

**Tolerancia de Sweep:** 3.0 pips. Permite near-miss sweeps que en condiciones reales de mercado son igualmente válidos.

**Persistencia:** Si se detecta un sweep durante London pero no hay confirmación en NY regular (08:00-14:00), el sweep se mantiene almacenado hasta las 18:00 para entrada extendida.

---

### PASO 3: NY Session Confirmation

Una vez detectada la manipulación, se espera confirmación estructural durante la sesión de New York.

#### Opción A: ChoCh Híbrido (Change of Character) - M5

Detección de cambio de carácter en timeframe M5 con filtro temporal:

**Filtro Temporal de Swings:**
- Solo se consideran los últimos **15 bars M5** para identificar swing highs/lows
- Previene comparaciones con swings obsoletos

**Detección de Swings:**
- Método de 3 barras: un high/low es swing si es mayor/menor que las barras adyacentes (±1)

**Tolerancia Dinámica:**
```
tolerance = max(rango_10_barras * 0.15, pip * 2.0)
```
Se adapta automáticamente a la volatilidad reciente.

| Dirección | Condición de Break | Tolerancia |
|-----------|-------------------|------------|
| **BUY (Bullish ChoCh)** | Close >= (last_swing_high - tolerance) | pip * 2.0 mínimo |
| **SELL (Bearish ChoCh)** | Close <= (last_swing_low + pip * 1.5) | 1.5 pips sobre swing low |

#### Opción B: Fractal Break (Fallback)

Si no se detecta ChoCh, se busca ruptura fractal en las últimas 3 velas H1:

| Dirección | Threshold | Condición |
|-----------|-----------|-----------|
| **BUY** | fractal_high - (pip * 3.0) | Close > threshold (zona de liquidez 3 pips debajo) |
| **SELL** | fractal_low + (pip * 1.0) | Close < threshold (zona de liquidez 1 pip arriba) |

> **Calibración actual:** Fractal SELL threshold en 1.0 pips. Valor óptimo entre 1.0-3.0 pips bajo investigación para balance entre distribución BUY/SELL y rentabilidad.

---

### PASO 4: Filtro de Entropía Shannon

Mide el desorden/aleatoriedad del mercado para evitar operar en regímenes caóticos.

**Cálculo:**
- Discretización de retornos en 10 bins
- Fórmula: H = -sum(p * log2(p))
- Ventana: últimas 50 barras

**Regla:**
- Si **H > 3.1** → Mercado demasiado aleatorio → **NO OPERAR**
- Si **H <= 3.1** → Régimen definido → Proceder con la señal

**Modo alternativo (Z-Score):**
- Si Z-score de entropía > 1.5 desviaciones estándar sobre la media → NO OPERAR

---

### PASO 5: Filtro ML (Machine Learning)

Cuando hay un modelo XGBoost entrenado y cargado:

- Si **confidence < 0.65** → Señal rechazada
- Si **confidence >= 0.65** → Señal aceptada con ajuste de riesgo (ver sección 7)

**Features del modelo (20 SMC features):**
PDH/PDL levels, sesiones activas, sweeps detectados, fractales, entropía, bias diario, y más.

---

## 6. Stop Loss y Take Profit

### Stop Loss (Dinámico por ML Confidence)

El SL se coloca en el nivel de manipulación (PDH/PDL) con un buffer en pips:

| Dirección | Fórmula SL |
|-----------|-----------|
| **BUY** | SL = PDL - (sl_pips * pip) |
| **SELL** | SL = PDH + (sl_pips * pip) |

**SL Dinámico por ML Confidence:**

| ML Confidence | SL Pips |
|---------------|---------|
| > 0.85 (alta confianza) | 8.0 pips (SL ajustado) |
| < 0.75 (baja confianza) | 12.0 pips (SL amplio) |
| 0.75 - 0.85 | 10.0 pips (base) |
| Sin modelo ML | 10.0 pips (base) |

### Take Profit (Lógica de Cascada)

El TP se determina en orden de prioridad:

1. **Fair Value Gap (FVG):** Si existe un FVG sin rellenar en las últimas 30 barras, se usa como "TP magnético"
   - Bullish FVG: gap donde Candle3.low > Candle1.high
   - Bearish FVG: gap donde Candle3.high < Candle1.low

2. **Liquidity Target (Fallback):** Swing high/low más cercano dentro de 50 barras en dirección del trade

3. **Porcentaje (Último recurso):** 0.5% de movimiento sobre el precio de entrada

### Risk-Reward Mínimo

- **Min RR:** 1.3:1 (optimizado Feb 2026)
- Si el RR inicial es < 1.3, el sistema intenta encontrar un TP alternativo en el siguiente nivel de liquidez
- Si aún así RR < 1.3, la señal se **descarta**

### Filtros de SL por Símbolo (Backtest Engine)

| Símbolo | SL Mínimo | SL Máximo |
|---------|-----------|-----------|
| EURUSD | 10 pips | 100 pips |
| XAUUSD | 100 pips | 5,000 pips |

Trades con SL fuera de estos rangos son rechazados automáticamente.

---

## 7. Gestión de Capital y Position Sizing

### Riesgo por Trade

| Escenario | Riesgo (%) |
|-----------|-----------|
| **Default (sin ML)** | 1.0% |
| ML Confidence > 0.85 + Entropía baja (Z < 0) | 1.5% |
| ML Confidence > 0.85 + Entropía alta (Z > 0) | 0.5% |
| ML Confidence 0.65-0.85 | 0.5% |

### Fórmula de Position Sizing (Percent Risk)

```
risk_amount = balance * (risk_percent / 100)
raw_lot = risk_amount / (sl_pips * pip_value)
lot = round(raw_lot / volume_step) * volume_step
lot = max(volume_min, min(lot, volume_max))
```

**Restricciones:**
- Lote mínimo: 0.01
- Lote máximo: 10.0
- Volume step: 0.01

### Ejemplo Práctico

```
Balance: $10,000
Riesgo: 1.0% = $100
SL: 15 pips en EURUSD
Pip Value: $10/pip

raw_lot = $100 / (15 * $10) = 0.6667
lot = round(0.6667 / 0.01) * 0.01 = 0.67

Riesgo real: 0.67 * 15 * $10 = $100.50
```

### Lot Distortion Check

Si el riesgo real (después del redondeo) excede **2x** el riesgo permitido, el trade se descarta. Esto previene que el redondeo de lote duplique la exposición.

```
actual_risk = lot * sl_pips * pip_value
allowed_risk = balance * (risk_percent / 100)

Si actual_risk > allowed_risk * 2.0 → TRADE RECHAZADO
```

---

## 8. Risk Management

### Circuit Breaker (Automático)

El sistema tiene un circuit breaker que detiene todas las operaciones automáticamente cuando se alcanzan umbrales críticos.

| Protección | Umbral | Acción |
|-----------|--------|--------|
| **Max Drawdown** | 10.0% del balance | Detiene todas las operaciones |
| **Pérdida Diaria** | 3.0% del balance inicial del día | Detiene operaciones hasta el siguiente día |
| **Overtrading** | 10 trades por hora | Rechaza nuevos trades hasta que pase 1 hora |

### Cálculo de Drawdown

```
drawdown = (balance - equity) / balance * 100

Si drawdown >= 10.0% → CIRCUIT BREAKER ACTIVADO
```

### Cálculo de Pérdida Diaria

```
daily_loss = (starting_balance - current_balance) / starting_balance * 100

Si daily_loss >= 3.0% → OPERACIONES SUSPENDIDAS HASTA MAÑANA
```

### Kill Switch (Emergencia Manual)

- Activación por API: `POST /api/v1/bot/kill`
- Efecto: detiene inmediatamente todas las operaciones
- Puede cerrar todas las posiciones abiertas al activarse
- Requiere desactivación explícita para reanudar

### Guards del Motor de Backtesting

| Guard | Umbral | Efecto |
|-------|--------|--------|
| Margin Call | Balance <= $0 | Detiene backtest |
| Drawdown Extremo | >= 95% | Detiene backtest (account blown) |
| SL fuera de rango | < Min o > Max por símbolo | Trade rechazado |
| RR insuficiente | < 1.0 (backtest) / < 1.3 (estrategia) | Trade rechazado |
| Lot distortion | > 2x riesgo permitido | Trade rechazado |

### Compatibilidad FTMO

Este plan de risk management está diseñado para cumplir con las reglas de las prop firms:

| Regla FTMO | Nuestro Límite | Margen |
|------------|---------------|--------|
| Max Daily Loss: 5% | **3.0%** | 2% de margen |
| Max Total Loss: 10% | **10.0%** | En el límite (ajustar a 8% si se desea margen) |
| Min Trading Days: 4 | Operación diaria automatizada | Cumple |

---

## 9. Flujo de Ejecución

### Secuencia Pre-Trade

```
1. Filtro de Noticias
   └─ ¿High Impact event en ±5 min? → Si: SKIP

2. Carga de Datos
   └─ 200 barras H1 + 200 barras M5 (para ChoCh)

3. Generación de Señal
   └─ strategy.generate_signal(df, symbol, timeframe)
   └─ Aplica los 5 pasos de entrada (Bias → Manipulation → Confirmation → Entropy → ML)

4. Validación de Riesgo
   └─ risk.check_trade_allowed(balance, equity)
   └─ Circuit breaker, kill switch, overtrading check

5. Cálculo de Lote
   └─ risk.calculate_lot_size(balance, equity, sl_pips, pip_value)
   └─ ML risk override si aplica

6. Ejecución
   └─ mt5.send_market_order(symbol, direction, lot, sl, tp)

7. Registro
   └─ risk.record_trade() (para detección de overtrading)
   └─ Audit log en base de datos
```

### Intervalo de Loop

El bot ejecuta su loop de evaluación cada **60 segundos**.

### Cierre por Tiempo

- Si el trade no alcanza SL ni TP antes de las **16:30 Bogotá (21:30 UTC)**, se cierra al precio de mercado.
- El flag de cierre se resetea a medianoche.

---

## 10. Resultados de Backtesting (Validación con Datos Reales)

Todos los backtests fueron ejecutados con datos reales de MetaTrader 5, incluyendo spread, comisión ($7/lote) y slippage simulado.

### EURUSD H1 - Balance Inicial: $10,000

| Métrica | 20k Barras | 10k Barras | 7k Barras |
|---------|-----------|-----------|----------|
| **Total Trades** | 146 | 304 | 41 |
| **Win Rate** | 56.16% | 49.67% | 73.17% |
| **Profit Factor** | 1.36 | 1.31 | 3.38 |
| **Sharpe Ratio** | 2.25 | - | 8.33 |
| **Max Drawdown** | 7.89% | - | - |
| **Net Profit** | +$1,275.23 | +$2,436.84 | +$1,526.33 |
| **Retorno** | +12.75% | +24.37% | +15.26% |

### Distribución BUY/SELL (20k Barras)

| Dirección | Trades | Porcentaje |
|-----------|--------|-----------|
| BUY | 26 | 17.8% |
| SELL | 120 | 82.2% |

> **Nota de Calibración:** Existe un desbalance hacia SELL bajo investigación activa. El threshold de Fractal SELL está en 1.0 pips, buscando el valor óptimo entre 1.0-3.0 pips para equilibrar distribución sin sacrificar rentabilidad.

### Métricas Avanzadas Disponibles

| Métrica | Descripción |
|---------|-------------|
| **Sortino Ratio** | Ratio ajustado por volatilidad negativa (solo pérdidas) |
| **Calmar Ratio** | Retorno anualizado / Max Drawdown |
| **VaR 95%** | Value at Risk - peor pérdida esperada al 95% de confianza |
| **CVaR 95%** | Expected Shortfall - promedio de pérdidas peores que el VaR |

### Análisis por Sesión

Los trades se categorizan automáticamente por sesión:
- **London (07:00-16:30 UTC):** Trades de manipulación temprana
- **New York (13:00-19:00 UTC):** Trades de confirmación principal

Se trackean win rate, profit factor y net profit por sesión para identificar cuál genera mayor rentabilidad.

---

## 11. Checklist Pre-Sesión

Antes de iniciar cada día de trading:

- [ ] Verificar conexión con MetaTrader 5
- [ ] Confirmar que el bot está activo (`GET /api/v1/bot/status`)
- [ ] Revisar calendario económico del día (noticias High Impact)
- [ ] Verificar que no hay posiciones abiertas del día anterior
- [ ] Confirmar balance y equity actuales
- [ ] Verificar que el circuit breaker no está activado
- [ ] Revisar la vela D1 del día anterior (bias esperado)
- [ ] Confirmar horario de verano/invierno (ajuste UTC si aplica)

### Condiciones para NO Operar

- Lunes antes de las 08:00 Bogotá (mercado con baja liquidez)
- Viernes después de las 14:00 Bogotá (cierre semanal, spreads amplios)
- Días de FOMC/NFP si el sistema no tiene el schedule actualizado
- Drawdown diario cercano al 2.5% (acercándose al cap del 3%)
- Problemas de conexión con MT5 o el broker

---

## 12. Reglas Psicológicas y Disciplina

### Reglas Inquebrantables

1. **No intervenir manualmente** en trades abiertos por el bot. El sistema tiene SL, TP y time-close definidos.

2. **No revenge trading.** Si el circuit breaker se activa, NO desactivarlo manualmente para seguir operando. Esperar al siguiente día.

3. **No modificar parámetros durante la sesión.** Los cambios de configuración se hacen FUERA de horario de mercado, después de análisis con datos.

4. **No aumentar el riesgo después de pérdidas.** El sistema de ML ajusta el riesgo basado en datos, no en emociones.

5. **Respetar el kill switch.** Si se activa por emergencia, investigar la causa antes de reanudar.

6. **No operar pares no validados.** Solo EURUSD está completamente optimizado. Otros pares requieren backtesting dedicado antes de ir a producción.

### Mentalidad

- Un trade perdedor no es un error si cumplió todas las reglas del plan.
- Las rachas perdedoras son estadísticamente normales (incluso con 56% de win rate, es posible tener 5-6 pérdidas consecutivas).
- El edge se materializa en cientos de trades, no en uno solo.
- Confiar en el proceso: la estrategia está validada con datos reales.

---

## 13. Revisión y Mejora Continua

### Revisión Semanal

- Revisar trades de la semana en el Audit Log
- Comparar win rate real vs backtested (56.16% es el benchmark)
- Analizar distribución BUY/SELL (objetivo: ratio 0.8-1.2)
- Verificar que el drawdown no excedió el 5%
- Revisar trades rechazados (debug_stats) para identificar filtros excesivos

### Revisión Mensual

- Ejecutar backtest con datos del mes actual
- Comparar métricas reales vs simuladas
- Evaluar si los parámetros necesitan re-calibración
- Revisar performance por sesión (London vs NY)
- Actualizar schedule de noticias (`news_schedule.json`)

### Calibración en Progreso (Marzo 2026)

| Parámetro | Valor Actual | Rango de Investigación | Objetivo |
|-----------|-------------|----------------------|---------|
| Fractal SELL threshold | 1.0 pips | 1.0 - 3.0 pips | Equilibrar BUY/SELL sin perder rentabilidad |
| ChoCh SELL tolerance | 1.5 pips | 1.0 - 2.0 pips | Impacto mínimo (mayoría de SELL vienen de Fractal) |
| Min RR | 1.3 | 1.0 - 1.5 | Optimizado en Feb 2026, estable |

### Criterios para Modificar Parámetros

Solo se modifican parámetros cuando:
1. Se tiene un backtest de al menos 7,000 barras que justifique el cambio
2. El cambio mejora Net Profit sin degradar Sharpe Ratio > 20%
3. El cambio no aumenta Max Drawdown por encima del 10%
4. Se valida con al menos 2 datasets independientes (ej. 7k y 20k barras)

---

## Apéndice A: Parámetros Técnicos Completos

```
BiasStrategy V1 Parameters:
├── entropy_threshold: 3.1
├── entropy_window: 50 bars
├── choch_lookback: 60 M5 bars
├── min_rr: 1.3
├── sl_pips_base: 10.0 pips
├── min_ml_confidence: 0.65
├── sweep_tolerance_pips: 3.0
├── fvg_lookback: 30 bars
├── london_start_hour: 2 (Bogotá)
├── london_end_hour: 11 (Bogotá)
├── ny_start_hour: 8 (Bogotá)
├── ny_end_hour: 14 (Bogotá)
├── close_time_utc: (21, 30)
├── temporal_swing_filter: 15 M5 bars
├── dynamic_tolerance: max(range*0.15, pip*2.0)
├── choch_sell_threshold: pip * 1.5
├── fractal_buy_threshold: pip * 3.0 (below high)
└── fractal_sell_threshold: pip * 1.0 (above low)

Risk Management:
├── risk_per_trade: 1.0%
├── max_daily_loss: 3.0%
├── max_drawdown: 10.0%
├── max_trades_per_hour: 10
├── lot_distortion_factor: 2.0x
├── volume_min: 0.01
└── volume_max: 10.0

Simulation Costs (EURUSD):
├── spread: 1.2 pips
├── commission: $7.0/lot
├── slippage: 0-0.3 pips (random)
├── pip_value: $10.0/pip
└── point: 0.0001
```

---

## Apéndice B: Glosario

| Término | Definición |
|---------|-----------|
| **PDH** | Previous Day High - máximo del día anterior |
| **PDL** | Previous Day Low - mínimo del día anterior |
| **ChoCh** | Change of Character - cambio de estructura de mercado |
| **FVG** | Fair Value Gap - gap de precio sin rellenar |
| **SMC** | Smart Money Concepts - metodología institucional |
| **Sweep** | Barrido de liquidez más allá de un nivel clave |
| **Doji** | Vela de indecisión (cuerpo < 20% del rango) |
| **Fractal** | Punto de swing identificado con el método de 3 barras |
| **Shannon Entropy** | Medida de desorden/aleatoriedad del mercado |
| **Circuit Breaker** | Mecanismo automático de parada por exceso de riesgo |
| **Kill Switch** | Parada de emergencia manual |
| **Pip** | Unidad mínima de movimiento de precio |
| **Lot** | Unidad de volumen de trading |
| **Drawdown** | Caída desde el punto máximo de equity |
| **Profit Factor** | Ganancia bruta / Pérdida bruta |
| **Sharpe Ratio** | Retorno ajustado por riesgo |
| **Sortino Ratio** | Sharpe ajustado solo por volatilidad negativa |
| **VaR** | Value at Risk - pérdida máxima esperada a un nivel de confianza |
| **CVaR** | Conditional VaR - pérdida promedio cuando se supera el VaR |

---

*Documento generado: Marzo 2026 | Versión 1.0*
*Próxima revisión programada: Abril 2026*

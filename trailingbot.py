import time
import ccxt

# ==========================================
# CONFIGURACIÓN DE TUS PARÁMETROS
# ==========================================
API_KEY = 'APUo3mk2TkVESX0dJ3YwKTIHMr87ItzHprV6YIJPIG1KBjelReLWS9VErArFD6sc'
SECRET_KEY = 'dLwxyjsZK3eWPgk7iWLBeL7MgYTZtROgwGaehbOh5FtqvzqxvZUj0Bac7wzabHnx'

SYMBOL = 'BTC/USDT' # 1. La moneda / par que estás operando
ACTIVATION_DIST_PCT = 2.35 # 2. Distancia de activación en % a favor desde tu precio promedio
CALLBACK_RATE_PCT = 0.50 # 3. Tasa de callback en % para proteger las ganancias

# Inicializar cliente de Binance Futures
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'options': {'defaultType': 'future'}
})
exchange.adjustForTimeDifference = True
exchange.load_time_difference()

last_entry_price = None
last_position_size = 0

def run_trailing_manager():
    time.sleep(10)
    global last_entry_price, last_position_size
    
    print(f"=== GESTOR DE TRAILING STOP INICIADO PARA {SYMBOL} ===")
    print(f"Distancia de activación: {ACTIVATION_DIST_PCT}% | Callback: {CALLBACK_RATE_PCT}%")
    print("Monitoreando posición y recompras en Binance...\n")
    
    while True:
        try:
            # 1. Consultar posición actual en Binance Futures
            positions = exchange.fetch_positions([SYMBOL])
            pos = positions[0] if positions else None
            
            # Si no hay posición activa (tamaño 0)
            if not pos or float(pos['contracts']) == 0:
                if last_position_size != 0:
                    print(f"\n[✔] Operación cerrada detectada. Esperando nueva entrada...")
                    last_entry_price = None
                    last_position_size = 0
                time.sleep(10)
                continue

            current_size = float(pos['contracts'])
            entry_price = float(pos['entryPrice'])
            side = pos['side'].lower() # Detecta automáticamente 'short' o 'long'

            # 2. Detectar si hubo cambios (entrada inicial o ejecución de una recompra)
            if entry_price != last_entry_price or current_size != last_position_size:
                print(f"\n" + "-"*50)
                print(f"[!] CAMBIO DETECTADO EN LA POSICIÓN ({side.upper()})")
                print(f" - Nuevo Precio Promedio: {entry_price}")
                print(f" - Tamaño Total de Contratos: {current_size}")

                # Cancelar órdenes de Trailing previas para evitar conflictos
                try:
                    exchange.cancel_all_orders(SYMBOL)
                except Exception:
                    pass

                # 3. Calcular Precio de Activation (Trigger) según la dirección
                if side == 'short':
                    # Para SHORT: El precio baja a favor. El trigger va por debajo del precio promedio
                    trigger_price = entry_price * (1 - (ACTIVATION_DIST_PCT / 100))
                    order_side = 'buy' # Para cerrar un Short se ejecuta una orden de compra
                else: # 'long'
                    # Para LONG: El precio sube a favor. El trigger va por encima del precio promedio
                    trigger_price = entry_price * (1 + (ACTIVATION_DIST_PCT / 100))
                    order_side = 'sell' # Para cerrar un Long se ejecuta una orden de venta

                # Guardamos los nuevos valores para no repetir el aviso
                last_entry_price = entry_price
                last_position_size = current_size

                print(f" -> Activando Trailing | Precio de Activación (Trigger): {trigger_price}")

                # Colocar la orden Trailing Stop Market en Binance Futures
                try:
                    params = {
                        'activationPrice': float(trigger_price),
                        'callbackRate': float(CALLBACK_RATE_PCT),
                    }
                    order = exchange.create_order(
                        symbol=SYMBOL,
                        type='TRAILING_STOP_MARKET',
                        side=order_side,
                        amount=current_size,
                        params=params
                    )
                    print(f"[✔] Orden Trailing Stop colocada exitosamente en Binance.")
                except Exception as e:
                    print(f"[X] Error al colocar la orden Trailing: {e}")

            time.sleep(10)

        except Exception as e:
            print(f"[!] Error en el ciclo: {e}")
            time.sleep(10)

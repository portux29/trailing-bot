import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import ccxt

# --- Mini servidor web fantasma para cumplir con el requisito de puertos de Render (Gratis) ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot de Trailing Stop activo y funcionando.")
        
    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"[*] Servidor HTTP fantasma iniciado en el puerto {port}")
    server.serve_forever()

# Arrancamos el servidor web en segundo plano (hilo independiente)
web_thread = threading.Thread(target=run_web_server, daemon=True)
web_thread.start()

# --- Configuración del Bot ---
SYMBOL = 'XRP/USDT:USDT' # Cambia aquí tu par si usas otro (ej: BTC/USDT:USDT)
ACTIVATION_DIST_PCT = 1.0 # Distancia de activación (%)
CALLBACK_RATE_PCT = 0.5 # Callback (%)

# Inicializar conexión con Binance Futures
exchange = ccxt.binance({
    'apiKey': os.environ.get('BINANCE_API_KEY', 'TU_API_KEY'),
    'secret': os.environ.get('BINANCE_SECRET', 'TU_SECRET'),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
    }
})

last_entry_price = None
last_position_size = 0

def run_trailing_manager():
    time.sleep(10) # Pausa inicial de seguridad
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

                # 3. Calcular Precio de Activación (Trigger) según la dirección
                if side == 'short':
                    trigger_price = entry_price * (1 - (ACTIVATION_DIST_PCT / 100))
                    order_side = 'buy'
                else: 
                    trigger_price = entry_price * (1 + (ACTIVATION_DIST_PCT / 100))
                    order_side = 'sell'

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

if __name__ == "__main__":
    run_trailing_manager()

        except Exception as e:
            print(f"[!] Error en el ciclo: {e}")
            time.sleep(10)

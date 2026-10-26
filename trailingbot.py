import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import ccxt

# Servidor web fantasma para Render (Plan Gratuito)
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot activo.")
        
    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

# Iniciar servidor web en segundo plano
threading.Thread(target=run_web_server, daemon=True).start()

# Configuración
SYMBOL = 'XRP/USDT:USDT'
ACTIVATION_DIST_PCT = 1.0
CALLBACK_RATE_PCT = 0.5

exchange = ccxt.binance({
    'apiKey': os.environ.get('BINANCE_API_KEY', 'TU_API_KEY'),
    'secret': os.environ.get('BINANCE_SECRET', 'TU_SECRET'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

last_entry_price = None
last_position_size = 0

def run_trailing_manager():
    time.sleep(10)
    global last_entry_price, last_position_size
    print("=== GESTOR DE TRAILING STOP INICIADO ===")
    
    while True:
        try:
            positions = exchange.fetch_positions([SYMBOL])
            pos = positions[0] if positions else None
            
            if not pos or float(pos['contracts']) == 0:
                if last_position_size != 0:
                    print("[✔] Operación cerrada. Esperando nueva entrada...")
                    last_entry_price = None
                    last_position_size = 0
                time.sleep(10)
                continue

            current_size = float(pos['contracts'])
            entry_price = float(pos['entryPrice'])
            side = pos['side'].lower()

            if entry_price != last_entry_price or current_size != last_position_size:
                print(f"[!] Cambio detectado en posición ({side.upper()}) | Precio: {entry_price} | Contratos: {current_size}")
                
                try:
                    exchange.cancel_all_orders(SYMBOL)
                except Exception:
                    pass

                if side == 'short':
                    trigger_price = entry_price * (1 - (ACTIVATION_DIST_PCT / 100))
                    order_side = 'buy'
                else:
                    trigger_price = entry_price * (1 + (ACTIVATION_DIST_PCT / 100))
                    order_side = 'sell'

                last_entry_price = entry_price
                last_position_size = current_size

                try:
                    exchange.create_order(
                        symbol=SYMBOL,
                        type='TRAILING_STOP_MARKET',
                        side=order_side,
                        amount=current_size,
                        params={'activationPrice': float(trigger_price), 'callbackRate': float(CALLBACK_RATE_PCT)}
                    )
                    print("[✔] Orden Trailing Stop colocada con éxito.")
                except Exception as e:
                    print(f"[X] Error al colocar orden: {e}")

            time.sleep(10)

        except Exception as e:
            print(f"[!] Error en el ciclo: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_trailing_manager()

        except Exception as e:
            print(f"[!] Error en el ciclo: {e}")
            time.sleep(10)

import threading
import subprocess
import sys
import time

def run_bot():
    subprocess.run([sys.executable, 'run.py'])

def run_web():
    subprocess.run([sys.executable, 'web_interface.py'])

if __name__ == '__main__':
    # Iniciar el bot en un hilo separado
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    print("Bot de Telegram iniciado en segundo plano")
    time.sleep(2)  # Esperar un poco para que el bot inicie
    
    # Iniciar la interfaz web
    print("Iniciando interfaz web...")
    run_web()
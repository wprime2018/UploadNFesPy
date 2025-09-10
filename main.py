import os
import sys
import json
import threading
import time
from pathlib import Path
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import subprocess

# Função para determinar se está executando como EXE
def is_running_as_exe():
    return hasattr(sys, '_MEIPASS')

# Função para obter o caminho base correto
def get_base_path():
    if is_running_as_exe():
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))
# Configurar logging para Windows
def setup_logging():
    base_path = get_base_path()
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                log_dir / "nfe_uploader.log",
                maxBytes=10*1024*1024,
                backupCount=5,
                encoding='utf-8'
            ),
            logging.StreamHandler()
        ]
    )

setup_logging()
logger = logging.getLogger(__name__)

# Verificar se está no ambiente virtual
def check_virtual_env():
    if not hasattr(sys, 'base_prefix') or sys.base_prefix == sys.prefix:
        logger.warning("Não está em ambiente virtual. Execute o build.bat primeiro.")
        print("⚠️  Execute build.bat para configurar o ambiente!")

check_virtual_env()

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    logger.error("Tkinter não está disponível")
    print("Tkinter não instalado. O programa requer interface gráfica.")
    sys.exit(1)

try:
    import pickle
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    import io
except ImportError as e:
    logger.error(f"Dependências do Google não instaladas: {e}")
    print("Execute: pip install google-auth google-api-python-client")
    sys.exit(1)

class NFeGoogleDriveUploader:

    def __init__(self):
        self.service = None
        self.scopes = ['https://www.googleapis.com/auth/drive.file']
        self.config_file = os.path.join(get_base_path(), "config.json")
        self.default_config = {
            "credentials_file": "",
            "source_directory": "",
            "drive_folder": "NFes_XML",
            "update_interval": 300,
            "auto_start": False,
            "minimize_to_tray": False
        }
        self.config = self.load_config()
        self.running = False
        self.upload_thread = None
        self.tray_icon = None

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for key, value in self.default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
        return self.default_config.copy()

    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info("Configuração salva")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar configuração: {e}")
            return False

    def authenticate(self):
        if not self.config['credentials_file'] or not os.path.exists(self.config['credentials_file']):
            logger.error("Arquivo de credenciais não encontrado")
            return False

        try:
            creds = None
            token_file = "token.pickle"
            
            if os.path.exists(token_file):
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.config['credentials_file'], self.scopes)
                    creds = flow.run_local_server(port=0)
                
                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)
            
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Autenticação realizada com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro na autenticação: {e}")
            return False

    def create_folder(self, folder_name, parent_folder_id=None):
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            logger.info(f"Pasta '{folder_name}' criada")
            return folder.get('id')
        except Exception as e:
            logger.error(f"Erro ao criar pasta: {e}")
            return None

    def find_folder(self, folder_name):
        try:
            query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            if folders:
                return folders[0]['id']
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar pasta: {e}")
            return None

    def upload_xml_file(self, file_path, folder_id=None):
        try:
            file_name = os.path.basename(file_path)
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            file_metadata = {'name': file_name}
            
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaIoBaseUpload(io.BytesIO(file_content), 
                                    mimetype='application/xml',
                                    resumable=True)
            
            file = self.service.files().create(body=file_metadata,
                                             media_body=media,
                                             fields='id').execute()
            
            logger.info(f"Arquivo '{file_name}' enviado!")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar {file_path}: {e}")
            return False

    def upload_nfe_xmls(self):
        if not self.authenticate():
            return False

        source_dir = self.config['source_directory']
        if not source_dir or not os.path.exists(source_dir):
            logger.error("Diretório de origem não existe")
            return False

        try:
            folder_id = self.find_folder(self.config['drive_folder'])
            if not folder_id:
                folder_id = self.create_folder(self.config['drive_folder'])
            
            if not folder_id:
                logger.error("Não foi possível criar pasta no Drive")
                return False

            source_path = Path(source_dir)
            xml_files = list(source_path.glob('**/*.xml'))
            
            if not xml_files:
                logger.warning("Nenhum arquivo XML encontrado")
                return True
            
            logger.info(f"Encontrados {len(xml_files)} arquivos XML")
            
            success_count = 0
            for xml_file in xml_files:
                if self.upload_xml_file(str(xml_file), folder_id):
                    success_count += 1
            
            logger.info(f"Upload: {success_count}/{len(xml_files)}")
            return True
            
        except Exception as e:
            logger.error(f"Erro durante upload: {e}")
            return False

    def start_auto_upload(self):
        if self.running:
            return

        self.running = True
        logger.info("Iniciando upload automático...")
        
        def upload_loop():
            while self.running:
                try:
                    self.upload_nfe_xmls()
                    time.sleep(self.config['update_interval'])
                except Exception as e:
                    logger.error(f"Erro no loop: {e}")
                    time.sleep(60)
        
        self.upload_thread = threading.Thread(target=upload_loop, daemon=True)
        self.upload_thread.start()

    def stop_auto_upload(self):
        self.running = False
        logger.info("Upload automático parado")

    def add_to_startup(self):
      """Adiciona o programa à inicialização do Windows"""
      try:
          import winreg
          import sys
          
          # Caminho para o executável
          exe_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
          
          # Chave do registro para inicialização
          key = winreg.HKEY_CURRENT_USER
          key_value = r"Software\Microsoft\Windows\CurrentVersion\Run"
          
          # Nome do registro
          app_name = "NFeUploader"
          
          # Abrir a chave
          with winreg.OpenKey(key, key_value, 0, winreg.KEY_SET_VALUE) as registry_key:
              winreg.SetValueEx(registry_key, app_name, 0, winreg.REG_SZ, exe_path)
          
          logger.info("Programa adicionado à inicialização do Windows")
          return True
          
      except Exception as e:
          logger.error(f"Erro ao adicionar à inicialização: {e}")
          return False

    def remove_from_startup(self):
        """Remove o programa da inicialização do Windows"""
        try:
            import winreg
            
            key = winreg.HKEY_CURRENT_USER
            key_value = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "NFeUploader"
            
            with winreg.OpenKey(key, key_value, 0, winreg.KEY_SET_VALUE) as registry_key:
                winreg.DeleteValue(registry_key, app_name)
            
            logger.info("Programa removido da inicialização do Windows")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao remover da inicialização: {e}")
            return False

class ConfigGUI:
    def __init__(self, root, uploader):
        self.root = root
        self.uploader = uploader
        self.setup_ui()
        self.setup_tray_icon()

    def setup_ui(self):
      self.root.title("NFe Uploader - Google Drive")
      self.root.geometry("800x550")  # Tela ainda maior
      self.root.resizable(True, True)

      main_frame = ttk.Frame(self.root, padding="25")
      main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
      
      # Configurar expansão
      self.root.columnconfigure(0, weight=1)
      self.root.rowconfigure(0, weight=1)
      main_frame.columnconfigure(1, weight=1)

      ttk.Label(main_frame, text="Upload de NFe para Google Drive", 
              font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=3, pady=(0, 25))

      # Credenciais
      ttk.Label(main_frame, text="Arquivo de Credenciais:").grid(row=1, column=0, sticky=tk.W, pady=8)
      self.cred_file_var = tk.StringVar(value=self.uploader.config['credentials_file'])
      cred_entry = ttk.Entry(main_frame, textvariable=self.cred_file_var, width=70)
      cred_entry.grid(row=1, column=1, padx=8, sticky=tk.EW)
      ttk.Button(main_frame, text="Procurar", command=self.browse_cred_file, width=10).grid(row=1, column=2, padx=8)

      # Pasta XMLs
      ttk.Label(main_frame, text="Pasta dos XMLs:").grid(row=2, column=0, sticky=tk.W, pady=8)
      self.source_dir_var = tk.StringVar(value=self.uploader.config['source_directory'])
      source_entry = ttk.Entry(main_frame, textvariable=self.source_dir_var, width=70)
      source_entry.grid(row=2, column=1, padx=8, sticky=tk.EW)
      ttk.Button(main_frame, text="Procurar", command=self.browse_source_dir, width=10).grid(row=2, column=2, padx=8)

      # Pasta Drive
      ttk.Label(main_frame, text="Pasta no Google Drive:").grid(row=3, column=0, sticky=tk.W, pady=8)
      self.drive_folder_var = tk.StringVar(value=self.uploader.config['drive_folder'])
      drive_entry = ttk.Entry(main_frame, textvariable=self.drive_folder_var, width=70)
      drive_entry.grid(row=3, column=1, padx=8, sticky=tk.EW)

      # Intervalo
      ttk.Label(main_frame, text="Intervalo (segundos):").grid(row=4, column=0, sticky=tk.W, pady=8)
      self.interval_var = tk.StringVar(value=str(self.uploader.config['update_interval']))
      interval_spin = ttk.Spinbox(main_frame, from_=60, to=3600, increment=60, 
                                textvariable=self.interval_var, width=15)
      interval_spin.grid(row=4, column=1, sticky=tk.W, padx=8)

      # Opções
      options_frame = ttk.Frame(main_frame)
      options_frame.grid(row=5, column=0, columnspan=3, pady=20, sticky=tk.W)
      
      self.auto_start_var = tk.BooleanVar(value=self.uploader.config['auto_start'])
      ttk.Checkbutton(options_frame, text="Iniciar automaticamente", 
                    variable=self.auto_start_var).pack(side=tk.LEFT, padx=(0, 40))
      
      self.minimize_var = tk.BooleanVar(value=self.uploader.config.get('minimize_to_tray', False))
      ttk.Checkbutton(options_frame, text="Minimizar para bandeja", 
                    variable=self.minimize_var).pack(side=tk.LEFT)

      # Botões - Agora com melhor espaçamento
      button_frame = ttk.Frame(main_frame)
      button_frame.grid(row=6, column=0, columnspan=3, pady=20)

      # Linha 1 de botões
      row1_frame = ttk.Frame(button_frame)
      row1_frame.pack(pady=8)
      
      ttk.Button(row1_frame, text="💾 Salvar Configuração", 
                command=self.save_config, width=18).pack(side=tk.LEFT, padx=6)
      ttk.Button(row1_frame, text="🔗 Testar Conexão", 
                command=self.test_connection, width=15).pack(side=tk.LEFT, padx=6)
      ttk.Button(row1_frame, text="📤 Upload Único", 
                command=self.single_upload, width=15).pack(side=tk.LEFT, padx=6)

      # Linha 2 de botões
      row2_frame = ttk.Frame(button_frame)
      row2_frame.pack(pady=8)
      
      ttk.Button(row2_frame, text="▶️ Iniciar Upload Automático", 
                command=self.start_auto_upload, width=18).pack(side=tk.LEFT, padx=6)
      ttk.Button(row2_frame, text="⏹️ Parar Upload", 
                command=self.stop_auto_upload, width=15).pack(side=tk.LEFT, padx=6)

      # Status
      self.status_var = tk.StringVar(value="✅ Pronto")
      status_label = ttk.Label(main_frame, textvariable=self.status_var, 
              foreground="green", font=("Arial", 10, "bold"))
      status_label.grid(row=7, column=0, columnspan=3, pady=20)

      # Configurar fechamento
      self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

      self.startup_var = tk.BooleanVar(value=self.is_in_startup())
      ttk.Checkbutton(options_frame, text="Iniciar com Windows", 
              variable=self.startup_var, command=self.toggle_startup).pack(side=tk.LEFT, padx=(0, 40))

    def setup_tray_icon(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
            self.tray_icon = pystray.Icon("nfe_uploader")
        except ImportError:
            self.tray_icon = None

    def on_closing(self):
        if self.minimize_var.get() and self.tray_icon:
            self.root.withdraw()
        else:
            self.root.quit()

    def browse_cred_file(self):
        filename = filedialog.askopenfilename(
            title="Selecione credentials.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.cred_file_var.set(filename)

    def browse_source_dir(self):
        directory = filedialog.askdirectory(title="Selecione a pasta com os XMLs")
        if directory:
            self.source_dir_var.set(directory)

    def save_config(self):
        try:
            self.uploader.config.update({
                'credentials_file': self.cred_file_var.get(),
                'source_directory': self.source_dir_var.get(),
                'drive_folder': self.drive_folder_var.get(),
                'update_interval': int(self.interval_var.get()),
                'auto_start': self.auto_start_var.get(),
                'minimize_to_tray': self.minimize_var.get()
            })
            
            if self.uploader.save_config():
                self.status_var.set("✅ Configuração salva!")
                messagebox.showinfo("Sucesso", "Configuração salva com sucesso!")
            else:
                self.status_var.set("❌ Erro ao salvar")
                
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {e}")

    def test_connection(self):
        self.status_var.set("🔗 Testando conexão...")
        self.root.update()
        
        if self.uploader.authenticate():
            self.status_var.set("✅ Conexão bem-sucedida!")
            messagebox.showinfo("Sucesso", "Conexão com Google Drive estabelecida!")
        else:
            self.status_var.set("❌ Falha na conexão")
            messagebox.showerror("Erro", "Falha na conexão. Verifique as credenciais.")

    def start_auto_upload(self):
        self.save_config()
        self.uploader.start_auto_upload()
        self.status_var.set("🔄 Upload automático iniciado!")
        messagebox.showinfo("Info", "Upload automático iniciado em segundo plano")

    def stop_auto_upload(self):
        self.uploader.stop_auto_upload()
        self.status_var.set("⏹️ Upload automático parado")
        messagebox.showinfo("Info", "Upload automático parado")

    def single_upload(self):
        self.save_config()
        self.status_var.set("📤 Iniciando upload único...")
        self.root.update()
        
        success = self.uploader.upload_nfe_xmls()
        if success:
            self.status_var.set("✅ Upload único concluído!")
            messagebox.showinfo("Sucesso", "Upload único concluído!")
        else:
            self.status_var.set("❌ Falha no upload")
            messagebox.showerror("Erro", "Falha no upload. Verifique os logs.")

    # Novos métodos
    def is_in_startup(self):
        """Verifica se o programa está na inicialização do Windows"""
        try:
            import winreg
            key = winreg.HKEY_CURRENT_USER
            key_value = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "NFeUploader"
            
            with winreg.OpenKey(key, key_value, 0, winreg.KEY_READ) as registry_key:
                try:
                    winreg.QueryValueEx(registry_key, app_name)
                    return True
                except FileNotFoundError:
                    return False
        except Exception:
            return False

    def toggle_startup(self):
        """Ativa/desativa inicialização com Windows"""
        if self.startup_var.get():
            success = self.uploader.add_to_startup()
        else:
            success = self.uploader.remove_from_startup()
        
        if not success:
            self.startup_var.set(not self.startup_var.get())  # Reverta se falhar
def main():
    root = tk.Tk()
    uploader = NFeGoogleDriveUploader()
    
    if uploader.config['auto_start']:
        logger.info("Iniciando automaticamente...")
        uploader.start_auto_upload()
    
    app = ConfigGUI(root, uploader)
    root.mainloop()

if __name__ == "__main__":
    main()
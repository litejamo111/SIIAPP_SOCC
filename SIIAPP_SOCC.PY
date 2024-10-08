import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import pyodbc
from tksheet import Sheet
import sys
import os
from dotenv import load_dotenv
from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
from cryptography.fernet import Fernet, InvalidToken
import logging

logging.basicConfig(filename='auth.log', level=logging.INFO)

# Check if .env file exists in the current directory
env_file_path = '.env' if os.path.isfile('.env') else '_internal/.env'

# Load .env file
load_dotenv(env_file_path)

# AD settings
AD_SERVER = os.getenv('AD_SERVER')
AD_DOMAIN = os.getenv('AD_DOMAIN')
AD_USER = os.getenv('AD_USER')
AD_PASSWORD = os.getenv('AD_PASSWORD')
ALLOWED_GROUPS = os.getenv('ALLOWED_GROUPS')
ALLOWED_USERS = os.getenv('ALLOWED_USERS')
# Retrieve the encryption key from the .env file
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
fernet = Fernet(ENCRYPTION_KEY)

# Ensure the encryption key is loaded
if ENCRYPTION_KEY is None:
    raise ValueError("No encryption key found in environment variables.")

#Generating decryption key
class MyTabView(ctk.CTkTabview):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Create tabs
        self.add("Seguimiento OC")
        self.add("Seguimiento sin OC")
        
        # Add widgets to tabs
        self.my_frame1 = MyFrame(master=self.tab("Seguimiento OC"), load_data_func=self.load_data_oc)
        self.my_frame1.pack(fill="both", expand=True)
        self.my_frame2 = MyFrame(master=self.tab("Seguimiento sin OC"), load_data_func=self.load_data_noc)
        self.my_frame2.pack(fill="both", expand=True)
        
    def load_data_oc(self, frame):
        cursor = None  # Initialize cursor with None
        conn = None  # Initialize conn with None
        try:
            # Connect to the database
            conn_str = (
                f"DRIVER={os.getenv('DB1_DRIVER')};"
                f"SERVER={os.getenv('DB1_SERVER')};"
                f"DATABASE={os.getenv('DB1_DATABASE')};"
                f"UID={os.getenv('DB1_UID')};"
                f"PWD={os.getenv('DB1_PWD')}"
            )
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()

            # Fetch data from the database using parameterized query
            query = """
                SELECT
                    vw_in_ordeabasdeta_with_uid.UID,
                    vw_in_ordeabasdeta_with_uid.[# OC],
                    vw_in_ordeabasdeta_with_uid.[CODIGO ITEM],
                    vw_in_ordeabasdeta_with_uid.[DESCRIPCION ITEM],
                    vw_in_ordeabasdeta_with_uid.[NIT PROVEEDOR],
                    vw_in_ordeabasdeta_with_uid.[DESCRIPCION PROVEEDOR],
                    vw_in_ordeabasdeta_with_uid.[UNIDADES PEDIDAS],
                    vw_in_ordeabasdeta_with_uid.[VALOR NETO],
                    vw_in_ordeabasdeta_with_uid.[FECHA COMPROMETIDA],
                    vw_in_ordeabasdeta_with_uid.[FECHA REQUERIDA],
                    vw_in_ordeabasdeta_with_uid.[ESTADO OC],
                    CON_SEG_OC.OCFSTATE,
                    CON_SEG_OC.COMMENTS
                FROM dbo.vw_in_ordeabasdeta_with_uid
                LEFT OUTER JOIN dbo.CON_SEG_OC
                    ON vw_in_ordeabasdeta_with_uid.UID = CON_SEG_OC.UID COLLATE Latin1_General_CI_AS
            """
            cursor.execute(query)
            data = cursor.fetchall()

            # Insert data into the Tksheet
            formatted_data = [
                [str(value) if value is not None else "" for value in row]
                for row in data
            ]

            frame.original_data = formatted_data
            frame.sheet.set_sheet_data(formatted_data)

            # Configure column widths
            frame.column_widths = [0, 140, 120, 500, 120, 500, 120, 120, 140, 140, 120, 160, 600]

            for i, width in enumerate(frame.column_widths):
                frame.sheet.column_width(column=i, width=width)

        except pyodbc.Error as e:
            print(f"An error occurred while loading data: {str(e)}", file=sys.stderr)
        finally:
            # Close the database connection and cursor
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def load_data_noc(self, frame):
        cursor = None  # Initialize cursor with None
        conn = None  # Initialize conn with None
        headers = [
            "UID",
            "# OP",
            "CODIGO ITEM",
            "DESCRIPCION ITEM",
            "NIT PROVEEDOR",
            "DESCRIPCION PROVEEDOR",
            "UNIDADES PENDIENTES",
            "VALOR NETO",
            "FECHA COMPROMETIDA",
            "FECHA REQUERIDA",
            "ESTADO OC",
            "ESTADO SEGUIMIENTO",
            "COMENTARIOS"
        ]
        frame.sheet.headers(headers)
        try:
            # Connect to the database
            conn_str = (
                f"DRIVER={os.getenv('DB1_DRIVER')};"
                f"SERVER={os.getenv('DB1_SERVER')};"
                f"DATABASE={os.getenv('DB1_DATABASE')};"
                f"UID={os.getenv('DB1_UID')};"
                f"PWD={os.getenv('DB1_PWD')}"
            )
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()

            # Fetch data from the database using parameterized query
            query = """
                SELECT
                    CONCAT(vw_Negativos.OP, vw_Negativos.item) AS UID
                    ,vw_Negativos.OP AS [# OP]
                    ,vw_Negativos.item AS [CODIGO ITEM]
                    ,in_items.itedesccort AS [DESCRIPCION ITEM]
                    ,NULL AS [NIT PROVEEDOR]
                    ,NULL AS [DESCRIPCION PROVEEDOR]
                    ,(vw_Negativos.Diferencia*-1) AS [UNIDADES PENDIENTES]
                    ,NULL AS [VALOR NETO]
                    ,NULL AS [FECHA COMPROMETIDA]
                    ,NULL AS [FECHA REQUERIDA]
                    ,NULL AS [ESTADO OC]
                    ,CON_SEG_OC.OCFSTATE
                    ,CON_SEG_OC.COMMENTS
                    FROM SIIAPP.dbo.vw_Negativos
                    LEFT OUTER JOIN SIIAPP.dbo.vw_in_ordeabasdeta_with_uid
                    ON vw_Negativos.item = vw_in_ordeabasdeta_with_uid.[CODIGO ITEM]
                    LEFT OUTER JOIN SIIAPP.dbo.CON_SEG_OC
                    ON CONCAT(vw_Negativos.OP, vw_Negativos.item) = CON_SEG_OC.UID COLLATE Latin1_General_CI_AS
                    INNER JOIN ssf_genericos.dbo.V_fp_pedidos
                    ON V_fp_pedidos.OP = vw_Negativos.OP
                    INNER JOIN ssf_genericos.dbo.in_items
                    ON vw_Negativos.item = in_items.itecodigo
                    WHERE vw_in_ordeabasdeta_with_uid.[# OC] IS NULL
                    AND in_items.itecompania = 01
                    ORDER BY vw_in_ordeabasdeta_with_uid.[# OC], [CODIGO ITEM]
            """
            cursor.execute(query)
            data = cursor.fetchall()

            # Insert data into the Tksheet
            formatted_data = [
                [str(value) if value is not None else "" for value in row]
                for row in data
            ]

            frame.original_data = formatted_data
            frame.sheet.set_sheet_data(formatted_data)

            # Check which columns are entirely null
            null_columns = []
            for col in range(len(formatted_data[0])):
                if all(row[col] == "" for row in formatted_data):
                    null_columns.append(col)

            # Configure column widths, setting width to 0 for null columns
            frame.column_widths = [0, 140, 120, 500, 120, 500, 120, 120, 140, 140, 120, 160, 600]
            for col in null_columns:
                frame.column_widths[col] = 0

            for i, width in enumerate(frame.column_widths):
                frame.sheet.column_width(column=i, width=width)

        except pyodbc.Error as e:
            print(f"An error occurred while loading data: {str(e)}", file=sys.stderr)
        finally:
            # Close the database connection and cursor
            if cursor:
                cursor.close()
            if conn:
                conn.close()

class ScrollableFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

class MyFrame(ctk.CTkFrame):
    def __init__(self, master, load_data_func, **kwargs):
        super().__init__(master, **kwargs)
        self.load_data_func = load_data_func

        # Create Tksheet widget
        self.sheet = Sheet(self)
        self.sheet.pack(fill="both", expand=True)

        self.filtered_data = []
        
        #FASES SEGUIMIENTO 0C
        self.fases = ["Cartera", "Homologacion", "Cotizacion", "Diseño", "Suministrado Por Cliente"]
        
        # Configure column headers
        headers = [
            "UID",
            "# OC",
            "CODIGO ITEM",
            "DESCRIPCION ITEM",
            "NIT PROVEEDOR",
            "DESCRIPCION PROVEEDOR",
            "UNIDADES PEDIDAS",
            "VALOR NETO",
            "FECHA COMPROMETIDA",
            "FECHA REQUERIDA",
            "ESTADO OC",
            "ESTADO SEGUIMIENTO",
            "COMENTARIOS"
        ]
        self.sheet.headers(headers)

        # Enable row selection
        self.sheet.enable_bindings(("single_select", "row_select", "arrowkeys"))

        # Create a scrollable frame
        self.scrollable_frame = ScrollableFrame(self)
        self.scrollable_frame.pack(fill="both", expand=True)

        # Create filter entry
        self.filter_entry = ctk.CTkEntry(
            self.scrollable_frame, placeholder_text="Buscar por # OC, CODIGO ITEM, ITEM, NIT, PROVEEDOR")
        self.filter_entry.pack(padx=10, pady=10, fill="x")
        self.filter_entry.bind("<Return>", self.filter_data)

        # Create buttons
        self.button_frame = ctk.CTkFrame(self.scrollable_frame)
        self.button_frame.pack(padx=10, pady=10, fill="x")

        self.create_child_button = ctk.CTkButton(
            self.button_frame, text="Crear Registro", command=self.create_child_record)
        self.create_child_button.pack(side="left", padx=5)

        self.edit_child_button = ctk.CTkButton(
            self.button_frame, text="Editar Registro", command=self.edit_child_record)
        self.edit_child_button.pack(side="left", padx=5)

        self.hot_reload_button = ctk.CTkButton(
            self.button_frame, text="Refrescar", command=self.reload_data)
        self.hot_reload_button.pack(side="left", padx=5)
        
        sorting_options = ["Sin Orden", "Ordenar Por Fecha"]
        self.sorting_button = ctk.CTkSegmentedButton(
            self.button_frame,
            values=sorting_options,
            command=self.toggle_sorting
        )
        self.sorting_button.pack(side="left", padx=5)

        self.sorting_button.set("Sin Orden")
        
        self.load_data()

    def load_data(self):
        self.load_data_func(self)

    def filter_data(self, event):
        search_text = self.filter_entry.get().lower()
        if search_text:
            self.filtered_data = [
                row for row in self.original_data
                if search_text in str(row[1]).lower() or  # Search by "# OP"
                search_text in str(row[2]).lower() or  # Search by "CODIGO ITEM"
                search_text in str(row[4]).lower() or  # Search by "NIT PROVEEDOR"
                search_text in str(row[3]).lower() or  # Search by "DESCRIPCION ITEM"
                search_text in str(row[5]).lower()     # Search by "DESCRIPCION PROVEEDOR"
            ]
            self.sheet.set_sheet_data(self.filtered_data)
            # Update column widths after filtering
            for i, width in enumerate(self.column_widths):
                if all(row[i] == "" for row in self.filtered_data):
                    self.sheet.column_width(column=i, width=0)
                else:
                    self.sheet.column_width(column=i, width=width)
        else:
            self.filtered_data = self.original_data
            self.sheet.set_sheet_data(self.filtered_data)
            # Update column widths after filtering
            for i, width in enumerate(self.column_widths):
                if all(row[i] == "" for row in self.filtered_data):
                    self.sheet.column_width(column=i, width=0)
                else:
                    self.sheet.column_width(column=i, width=width)
                
    def toggle_sorting(self, sorting_option):
        if sorting_option == "Sin Orden":
            sorted_data = (self.original_data if self.filtered_data==[] else self.filtered_data)
            self.sheet.set_sheet_data(sorted_data)
            # Update column widths after sorting
            for i, width in enumerate(self.column_widths):
                if all(row[i] == "" for row in sorted_data):
                    self.sheet.column_width(column=i, width=0)
                else:
                    self.sheet.column_width(column=i, width=width)
        elif sorting_option == "Ordenar Por Fecha":
            fecha_comprometida_index = self.sheet.headers().index("FECHA COMPROMETIDA")
            sorted_data = sorted((self.original_data if self.filtered_data==[] else self.filtered_data), key=lambda row: row[fecha_comprometida_index] if row[fecha_comprometida_index] != "" else "")
            self.sheet.set_sheet_data(sorted_data)
            # Update column widths after sorting
            for i, width in enumerate(self.column_widths):
                if all(row[i] == "" for row in sorted_data):
                    self.sheet.column_width(column=i, width=0)
                else:
                    self.sheet.column_width(column=i, width=width)
                    
    def create_child_record(self):
        selected_rows = self.sheet.get_selected_rows()
        if selected_rows:
            # Get the first selected row
            selected_row = next(iter(selected_rows))
            row_data = self.sheet.get_row_data(selected_row)
            uid_value = row_data[0]  # Assuming 'UID' is at index 0
            try:
                conn_str = (
                    f"DRIVER={os.getenv('DB1_DRIVER')};"
                    f"SERVER={os.getenv('DB1_SERVER')};"
                    f"DATABASE={os.getenv('DB1_DATABASE')};"
                    f"UID={os.getenv('DB1_UID')};"
                    f"PWD={os.getenv('DB1_PWD')}"
                )
                conn = pyodbc.connect(conn_str)
                cursor = conn.cursor()

                check_query = "SELECT COUNT(*) FROM CON_SEG_OC WHERE UID = ?"
                cursor.execute(check_query, uid_value)
                count = cursor.fetchone()[0]

                if count > 0:
                    messagebox.showerror("Error", "Ya existe un registro con este UID.")
                    return

            except pyodbc.Error as e:
                print(f"An error occurred while checking for existing UID: {str(e)}", file=sys.stderr)
                return
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

            # Create a new window for entering child record data
            child_window = ctk.CTkToplevel(self)
            child_window.title("Crear Registro de Seguimiento")

            # Add input fields for child record data
            ocfstate_entry = ctk.CTkComboBox(child_window, values=self.fases, state="readonly")
            comments_entry = ctk.CTkTextbox(child_window, height=50, width=200)
            comments_entry.configure(border_color='blue', border_width=0.5)

            # Grid view
            ocfstate_label = ctk.CTkLabel(child_window, text="Estado de Seguimiento:")
            ocfstate_label.grid(row=0, column=0, padx=5, pady=5)
            ocfstate_entry.grid(row=0, column=1, padx=5, pady=5)

            comments_label = ctk.CTkLabel(child_window, text="Comentarios:")
            comments_label.grid(row=1, column=0, padx=5, pady=5)
            comments_entry.grid(row=1, column=1, padx=5, pady=5)

            def save_child_record():
                ocfstate = ocfstate_entry.get()
                comments = comments_entry.get("0.0", "end")

                if not ocfstate:
                    messagebox.showerror("Error", "Por favor, ingrese el estado de seguimiento antes de guardar el registro.")
                    child_window.destroy()
                    return

                try:
                    # Insert the child record into the database using parameterized query
                    conn_str = (
                        f"DRIVER={os.getenv('DB1_DRIVER')};"
                        f"SERVER={os.getenv('DB1_SERVER')};"
                        f"DATABASE={os.getenv('DB1_DATABASE')};"
                        f"UID={os.getenv('DB1_UID')};"
                        f"PWD={os.getenv('DB1_PWD')}"
                    )
                    conn = pyodbc.connect(conn_str)
                    cursor = conn.cursor()

                    insert_query = """
                        INSERT INTO CON_SEG_OC (UID, OCFSTATE, COMMENTS)
                        VALUES (?, ?, ?)
                    """
                    params = (uid_value, ocfstate, comments)
                    cursor.execute(insert_query, params)
                    conn.commit()

                except pyodbc.Error as e:
                    print(f"An error occurred while saving child record: {str(e)}", file=sys.stderr)
                finally:
                    # Close the database connection and cursor
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()

                child_window.destroy()
                self.reload_data()

            save_button = ctk.CTkButton(child_window, text="Guardar", command=save_child_record)
            save_button.grid(row=2, column=0, columnspan=2, pady=10)
        else:
            messagebox.showinfo("Sin seleccion", "Porfavor eliga una fila para Crear un registro")

    def edit_child_record(self):
        selected_rows = self.sheet.get_selected_rows()
        if selected_rows:
            # Get the first selected row
            selected_row = next(iter(selected_rows))
            row_data = self.sheet.get_row_data(selected_row)
            uid_value = row_data[0]  # Assuming 'UID' is at index 0

            # Create a new window for editing child record data
            edit_window = ctk.CTkToplevel(self)
            edit_window.title("Editar Registro de Seguimiento")

            # Add input fields for child record data
            ocfstate_entry = ctk.CTkComboBox(edit_window, values=self.fases, state="readonly")
            ocfstate_entry.set(row_data[11])  # Pre-fill with existing data
            comments_entry = ctk.CTkTextbox(edit_window, height=50, width=200)
            comments_entry.insert("0.0", row_data[12])  # Pre-fill with existing data
            comments_entry.configure(border_color='blue', border_width=0.5)

            # Grid view
            ocfstate_label = ctk.CTkLabel(edit_window, text="Estado de Seguimiento:")
            ocfstate_label.grid(row=0, column=0, padx=5, pady=5)
            ocfstate_entry.grid(row=0, column=1, padx=5, pady=5)

            comments_label = ctk.CTkLabel(edit_window, text="Comentarios:")
            comments_label.grid(row=1, column=0, padx=5, pady=5)
            comments_entry.grid(row=1, column=1, padx=5, pady=5)

            def save_edited_child_record():
                ocfstate = ocfstate_entry.get()
                comments = comments_entry.get("0.0", "end")

                try:
                    # Update the child record in the database using parameterized query
                    conn_str = (
                        f"DRIVER={os.getenv('DB1_DRIVER')};"
                        f"SERVER={os.getenv('DB1_SERVER')};"
                        f"DATABASE={os.getenv('DB1_DATABASE')};"
                        f"UID={os.getenv('DB1_UID')};"
                        f"PWD={os.getenv('DB1_PWD')}"
                    )
                    conn = pyodbc.connect(conn_str)
                    cursor = conn.cursor()

                    update_query = """
                        UPDATE CON_SEG_OC
                        SET OCFSTATE = ?, COMMENTS = ?
                        WHERE UID = ?
                    """
                    params = (ocfstate, comments, uid_value)
                    cursor.execute(update_query, params)
                    conn.commit()

                except pyodbc.Error as e:
                    print(f"An error occurred while updating child record: {str(e)}", file=sys.stderr)
                finally:
                    # Close the database connection and cursor
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()

                edit_window.destroy()
                self.reload_data()

            save_button = ctk.CTkButton(edit_window, text="Guardar Cambios", command=save_edited_child_record)
            save_button.grid(row=2, column=0, columnspan=2, pady=10)
        else:
            messagebox.showinfo("Sin seleccion", "Porfavor eliga una fila para editar un registro")

    def reload_data(self):
        # Clear existing data
        self.sheet.set_sheet_data([])

        # Load updated data from the database
        self.load_data()

class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.username_entry = ctk.CTkEntry(self, placeholder_text="Nombre de usuario")
        self.username_entry.pack(pady=10)
        self.password_entry = ctk.CTkEntry(self, placeholder_text="Contraseña", show="*")
        self.password_entry.pack(pady=10)
        self.remember_var = tk.BooleanVar()  # Variable to track the checkbox state
        self.remember_checkbox = ctk.CTkCheckBox(self, text="Recordar mis credenciales", variable=self.remember_var)
        self.remember_checkbox.pack(pady=5)
        self.login_button = ctk.CTkButton(self, text="Login", command=self.authenticate)
        self.login_button.pack(pady=10)

        # Load saved credentials if available
        self.load_credentials()    
    
    def save_credentials(self):
        if self.remember_var.get():
            encrypted_username = fernet.encrypt(self.username_entry.get().encode())
            encrypted_password = fernet.encrypt(self.password_entry.get().encode())
            with open("credentials.txt", "wb") as f:
                f.write(encrypted_username + b"," + encrypted_password)

    def load_credentials(self):
        try:
            with open("credentials.txt", "rb") as f:
                data = f.read()
                encrypted_username, encrypted_password = data.split(b",")
                self.username = fernet.decrypt(encrypted_username).decode()
                self.password = fernet.decrypt(encrypted_password).decode()
                self.username_entry.insert(0, self.username)
                self.password_entry.insert(0, self.password)
        except FileNotFoundError:
            pass
        except (ValueError, InvalidToken):
            messagebox.showerror("Error", "Unable to decrypt credentials. Please enter the correct password.")
    
    def authenticate(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if authenticate_user(username, password):
            messagebox.showinfo("Login Exitoso", "Bienvenido!")
            self.save_credentials()  # Save credentials before showing the app frame
            self.master.show_app_frame()
        else:
            messagebox.showerror("Login Fallido", "Credenciales invalidas o acceso denegado.")

def authenticate_user(username, password):
    server = Server(os.getenv('AD_SERVER'), get_info=ALL)
    user = f'{os.getenv("AD_DOMAIN")}\\{username}'
    
    try:
        conn = Connection(server, user=user, password=password, authentication='NTLM', auto_bind=True)
        logging.info(f"LDAP bind successful for {username}.")

        # Check if user is in allowed users
        allowed_users = os.getenv('ALLOWED_USERS').split(',')
        if username in allowed_users:
            return True
        
        # Search base is set to the root of the domain
        search_base = f'DC={AD_DOMAIN.replace(".", ",DC=")}'
        
        conn.search(
            search_base,
            f'(sAMAccountName={username})',
            attributes=['memberOf'],
            search_scope=SUBTREE
        )
        
        if not conn.entries:
            logging.warning(f"User {username} not found in LDAP search.")
            return False

        user_groups = [entry.memberOf.values if isinstance(entry.memberOf, list) else [entry.memberOf] for entry in conn.entries]
        user_groups = [item for sublist in user_groups for item in sublist]

        allowed_groups = os.getenv('ALLOWED_GROUPS').split(',')

        for group in allowed_groups:
            if any(group in str(user_group) for user_group in user_groups):
                return True

    except Exception as e:
        logging.error(f"LDAP error for {username}: {e}")

    logging.warning(f"Access denied for {username}.")
    return False

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1000x600")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.login_frame = LoginFrame(master=self)
        self.login_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

    def show_app_frame(self):
        self.login_frame.destroy()
        self.geometry("1000x600")
        self.my_frame = MyTabView(master=self)
        self.my_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

app = App()
app.title("SIIAPP SEGUIMIENTO OC")
app.mainloop()

import json
import os
import sqlite3
from datetime import datetime, timedelta
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image

# Configuración visual
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SistemaPOSPro(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("⚡ FastFood POS Pro - Sistema de Control Central")
        self.geometry("1280x850")

        self.init_db()

        self.usuario_actual = None
        self.rol_actual = None
        self.user_id_actual = None
        self.carrito = []
        self.ruta_imagen_seleccionada = None
        self.usuario_id_edicion = None

        self.mostrar_login()

    # ==========================================
    # BASE DE DATOS Y MIGRACIONES
    # ==========================================
    def init_db(self):
        if not os.path.exists("imagenes"):
            os.makedirs("imagenes")

        self.conn = sqlite3.connect("restaurante.db")
        self.cursor = self.conn.cursor()

        # Tabla Usuarios
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                clave TEXT NOT NULL,
                nombre TEXT NOT NULL,
                rol TEXT NOT NULL
            )
        """)

        self.cursor.execute("SELECT COUNT(*) FROM usuarios")
        if self.cursor.fetchone()[0] == 0:
            usuarios_base = [
                ("mesero1", "1234", "Carlos Gómez", "mesero"),
                ("cocina1", "1234", "Chef Mario", "cocina"),
                ("caja1", "1234", "Ana Cajera", "caja"),
                ("multi1", "1234", "Juan Multitarea", "multitarea"),
                ("admin", "admin", "Administrador", "admin"),
            ]
            self.cursor.executemany(
                "INSERT INTO usuarios (usuario, clave, nombre, rol) VALUES (?, ?, ?, ?)",
                usuarios_base,
            )

        # Tabla Categorías / Secciones
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL
            )
        """)
        
        self.cursor.execute("SELECT COUNT(*) FROM categorias")
        if self.cursor.fetchone()[0] == 0:
            cats = [("Alitas & Entradas",), ("Hamburguesas",), ("Bebidas",), ("Porciones & Acompañantes",), ("General",)]
            self.cursor.executemany("INSERT INTO categorias (nombre) VALUES (?)", cats)

        # Tabla Salsas
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS salsas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL
            )
        """)
        
        self.cursor.execute("SELECT COUNT(*) FROM salsas")
        if self.cursor.fetchone()[0] == 0:
            salsas_base = [
                ("BBQ",), ("Picante",), ("Queso",), 
                ("Mostaza Miel",), ("Ajo y Hierbas",), ("Sin Salsa / Al Natural",)
            ]
            self.cursor.executemany("INSERT INTO salsas (nombre) VALUES (?)", salsas_base)

        # Tabla Productos
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL,
                categoria TEXT DEFAULT 'General',
                icono TEXT DEFAULT '🍔',
                imagen_path TEXT DEFAULT '',
                requiere_salsa INTEGER DEFAULT 0
            )
        """)

        try:
            self.cursor.execute("ALTER TABLE productos ADD COLUMN requiere_salsa INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        self.cursor.execute("SELECT COUNT(*) FROM productos")
        if self.cursor.fetchone()[0] == 0:
            prods_base = [
                ("Porción de Alitas (6 unidades)", 5.50, "Alitas & Entradas", "🍗", "", 1),
                ("Porción de Papas", 1.50, "Porciones & Acompañantes", "🍟", "", 0),
                ("Porción de Arroz", 1.00, "Porciones & Acompañantes", "🍚", "", 0),
                ("Porción de Ensalada", 1.25, "Porciones & Acompañantes", "🥗", "", 0),
            ]
            self.cursor.executemany(
                "INSERT INTO productos (nombre, precio, categoria, icono, imagen_path, requiere_salsa) VALUES (?, ?, ?, ?, ?, ?)",
                prods_base,
            )

        # Tabla Pedidos
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente TEXT NOT NULL,
                items TEXT NOT NULL,
                total REAL NOT NULL,
                estado TEXT DEFAULT 'pendiente',
                mesero TEXT DEFAULT 'Sistema',
                metodo_pago TEXT DEFAULT 'Efectivo',
                fecha_hora TEXT DEFAULT ''
            )
        """)

        # Tabla Métodos de Pago
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS metodos_pago (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL
            )
        """)

        self.cursor.execute("SELECT COUNT(*) FROM metodos_pago")
        if self.cursor.fetchone()[0] == 0:
            metodos_base = [
                ("Efectivo",),
                ("Transf. Banco de Loja",),
                ("Transf. Banco Pichincha",)
            ]
            self.cursor.executemany("INSERT INTO metodos_pago (nombre) VALUES (?)", metodos_base)

        # Tabla Cajas
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS cajas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cajero TEXT NOT NULL,
                monto_apertura REAL NOT NULL,
                monto_cierre REAL DEFAULT 0.0,
                ventas_efectivo REAL DEFAULT 0.0,
                fecha_apertura TEXT NOT NULL,
                fecha_cierre TEXT DEFAULT '',
                estado TEXT DEFAULT 'abierta'
            )
        """)

        self.conn.commit()

    # ==========================================
    # LOGIN & AUTENTICACIÓN
    # ==========================================
    def mostrar_login(self):
        for widget in self.winfo_children():
            widget.destroy()

        frame_login = ctk.CTkFrame(self, corner_radius=15, width=400, height=450)
        frame_login.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            frame_login,
            text="⚡ FastFood POS",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#10b981",
        ).pack(pady=(30, 5))
        ctk.CTkLabel(
            frame_login,
            text="Inicio de Sesión Centralizado",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        ).pack(pady=(0, 20))

        self.entry_user = ctk.CTkEntry(
            frame_login, placeholder_text="Usuario", width=280, height=45, corner_radius=10
        )
        self.entry_user.pack(pady=10)

        self.entry_pass = ctk.CTkEntry(
            frame_login, placeholder_text="Contraseña", show="*", width=280, height=45, corner_radius=10
        )
        self.entry_pass.pack(pady=10)

        btn_login = ctk.CTkButton(
            frame_login,
            text="INGRESAR AL SISTEMA",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            width=280,
            height=45,
            corner_radius=10,
            command=self.validar_login,
        )
        btn_login.pack(pady=25)

    def validar_login(self):
        user = self.entry_user.get().strip()
        clave = self.entry_pass.get().strip()

        self.cursor.execute(
            "SELECT id, nombre, rol FROM usuarios WHERE usuario=? AND clave=?",
            (user, clave),
        )
        res = self.cursor.fetchone()

        if res:
            self.user_id_actual = res[0]
            self.usuario_actual = res[1]
            self.rol_actual = res[2]
            self.construir_interfaz_principal()
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos.")

    def construir_interfaz_principal(self):
        for widget in self.winfo_children():
            widget.destroy()

        header = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#1e293b")
        header.pack(fill="x", side="top")

        ctk.CTkLabel(
            header,
            text="⚡ FastFood POS Pro",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#10b981",
        ).pack(side="left", padx=20)

        btn_logout = ctk.CTkButton(
            header,
            text="Cerrar Sesión ➔",
            width=110,
            height=32,
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=self.mostrar_login,
        )
        btn_logout.pack(side="right", padx=20)

        ctk.CTkLabel(
            header,
            text=f"👤 {self.usuario_actual} ({self.rol_actual.upper()})",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white",
        ).pack(side="right", padx=15)

        self.main_container = ctk.CTkFrame(self, fg_color="#0f172a")
        self.main_container.pack(fill="both", expand=True, padx=15, pady=15)

        if self.rol_actual == "mesero":
            self.vista_mesero()
        elif self.rol_actual == "cocina":
            self.vista_cocina()
        elif self.rol_actual == "caja":
            self.vista_caja()
        elif self.rol_actual == "multitarea":
            self.vista_multitarea()
        elif self.rol_actual == "admin":
            self.vista_admin_con_pestanas()

    # ==========================================
    # VISTA MULTITAREA
    # ==========================================
    def vista_multitarea(self):
        tabview = ctk.CTkTabview(self.main_container)
        tabview.pack(fill="both", expand=True)

        tabview.add("📝 Tomar Pedido")
        tabview.add("💰 Cobros y Caja")
        tabview.add("📋 Lista de Pedidos")

        f_pedido = ctk.CTkFrame(tabview.tab("📝 Tomar Pedido"), fg_color="transparent")
        f_pedido.pack(fill="both", expand=True)
        self.construir_modulo_pedido(f_pedido, es_multitarea=True)

        self.f_caja_multi = ctk.CTkFrame(tabview.tab("💰 Cobros y Caja"), fg_color="transparent")
        self.f_caja_multi.pack(fill="both", expand=True)
        self.construir_modulo_caja(self.f_caja_multi)

        self.f_lista_multi = ctk.CTkFrame(tabview.tab("📋 Lista de Pedidos"), fg_color="transparent")
        self.f_lista_multi.pack(fill="both", expand=True)
        self.construir_modulo_lista_pedidos(self.f_lista_multi)

    # ==========================================
    # VISTA ADMINISTRADOR
    # ==========================================
    def vista_admin_con_pestanas(self):
        def al_cambiar_pestana(pestana_seleccionada):
            if pestana_seleccionada == "📊 Reportes":
                self.actualizar_reportes()
            elif pestana_seleccionada == "👥 Usuarios & Personal":
                self.actualizar_tabla_usuarios()
            elif pestana_seleccionada == "🍔 Gestión de Menú":
                self.actualizar_secciones_combo()
                self.actualizar_lista_menu_admin()
            elif pestana_seleccionada == "🥫 Gestión de Salsas":
                self.actualizar_lista_salsas()

        self.tabview_admin = ctk.CTkTabview(self.main_container, command=al_cambiar_pestana)
        self.tabview_admin.pack(fill="both", expand=True)

        self.tabview_admin.add("📊 Reportes")
        self.tabview_admin.add("👥 Usuarios & Personal")
        self.tabview_admin.add("🍔 Gestión de Menú")
        self.tabview_admin.add("🥫 Gestión de Salsas")
        self.tabview_admin.add("📝 Pedido Especial/Libre")
        self.tabview_admin.add("💳 Formas de Pago")

        self.scroll_reportes = ctk.CTkScrollableFrame(self.tabview_admin.tab("📊 Reportes"), fg_color="transparent")
        self.scroll_reportes.pack(fill="both", expand=True)

        self.container_usuarios = ctk.CTkFrame(self.tabview_admin.tab("👥 Usuarios & Personal"), fg_color="transparent")
        self.container_usuarios.pack(fill="both", expand=True)

        self.container_menu_admin = ctk.CTkFrame(self.tabview_admin.tab("🍔 Gestión de Menú"), fg_color="transparent")
        self.container_menu_admin.pack(fill="both", expand=True)

        self.container_salsas_admin = ctk.CTkFrame(self.tabview_admin.tab("🥫 Gestión de Salsas"), fg_color="transparent")
        self.container_salsas_admin.pack(fill="both", expand=True)

        f_pedido_admin = ctk.CTkFrame(self.tabview_admin.tab("📝 Pedido Especial/Libre"), fg_color="transparent")
        f_pedido_admin.pack(fill="both", expand=True)
        self.construir_modulo_pedido(f_pedido_admin, es_multitarea=True)

        self.container_pagos_admin = ctk.CTkFrame(self.tabview_admin.tab("💳 Formas de Pago"), fg_color="transparent")
        self.container_pagos_admin.pack(fill="both", expand=True)

        self.vista_reportes()
        self.vista_gestion_usuarios()
        self.vista_gestion_menu()
        self.vista_gestion_salsas()
        self.vista_gestion_metodos_pago()

    # ==========================================
    # 🥫 GESTIÓN DE SALSAS
    # ==========================================
    def vista_gestion_salsas(self):
        for w in self.container_salsas_admin.winfo_children():
            w.destroy()

        f_left = ctk.CTkFrame(self.container_salsas_admin, width=350)
        f_left.pack(side="left", fill="y", padx=10, pady=10)

        ctk.CTkLabel(f_left, text="🥫 Registrar Nueva Salsa", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15, padx=15)

        self.entry_nueva_salsa = ctk.CTkEntry(f_left, placeholder_text="Ej: Salsa de Miel y Ajo", height=40)
        self.entry_nueva_salsa.pack(fill="x", padx=15, pady=10)

        btn_guardar_salsa = ctk.CTkButton(
            f_left, text="💾 Guardar Salsa", fg_color="#10b981", command=self.guardar_salsa
        )
        btn_guardar_salsa.pack(fill="x", padx=15, pady=10)

        f_right = ctk.CTkFrame(self.container_salsas_admin)
        f_right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(f_right, text="📋 Salsas Registradas en el Sistema", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15, padx=15)

        self.scroll_salsas = ctk.CTkScrollableFrame(f_right, fg_color="transparent")
        self.scroll_salsas.pack(fill="both", expand=True, padx=15, pady=10)

        self.actualizar_lista_salsas()

    def guardar_salsa(self):
        nombre = self.entry_nueva_salsa.get().strip()
        if not nombre:
            return messagebox.showwarning("Atención", "Ingresa el nombre de la salsa.")
        try:
            self.cursor.execute("INSERT INTO salsas (nombre) VALUES (?)", (nombre,))
            self.conn.commit()
            self.entry_nueva_salsa.delete(0, "end")
            self.actualizar_lista_salsas()
            messagebox.showinfo("Éxito", f"Salsa '{nombre}' agregada correctamente.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Esta salsa ya está registrada.")

    def actualizar_lista_salsas(self):
        for w in self.scroll_salsas.winfo_children():
            w.destroy()

        self.cursor.execute("SELECT id, nombre FROM salsas")
        for s_id, nom in self.cursor.fetchall():
            row = ctk.CTkFrame(self.scroll_salsas, fg_color="#1e293b", height=40)
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(row, text=f"🥫  {nom}", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15)

            btn_del = ctk.CTkButton(
                row, text="🗑 Eliminar", width=80, fg_color="#ef4444", command=lambda i=s_id: self.eliminar_salsa(i)
            )
            btn_del.pack(side="right", padx=10)

    def eliminar_salsa(self, s_id):
        self.cursor.execute("DELETE FROM salsas WHERE id = ?", (s_id,))
        self.conn.commit()
        self.actualizar_lista_salsas()

    # ==========================================
    # REPORTES
    # ==========================================
    def vista_reportes(self):
        for w in self.scroll_reportes.winfo_children():
            w.destroy()

        filter_frame = ctk.CTkFrame(self.scroll_reportes, fg_color="#1e293b")
        filter_frame.pack(fill="x", pady=(0, 15), padx=5)

        ctk.CTkLabel(filter_frame, text="📅 Rango Rápido:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(15, 5), pady=10)

        self.combo_filtro_fecha = ctk.CTkOptionMenu(
            filter_frame,
            values=["Hoy", "Ayer", "Últimos 7 días", "Todos los Tiempos", "Día Específico"],
            command=self.al_cambiar_opcion_filtro,
            width=140
        )
        self.combo_filtro_fecha.pack(side="left", padx=5, pady=10)

        ctk.CTkLabel(filter_frame, text="📆 Día Específico (AAAA-MM-DD):", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(20, 5), pady=10)

        hoy_str = datetime.now().strftime("%Y-%m-%d")
        self.entry_fecha_especifica = ctk.CTkEntry(filter_frame, placeholder_text="YYYY-MM-DD", width=120)
        self.entry_fecha_especifica.insert(0, hoy_str)
        self.entry_fecha_especifica.pack(side="left", padx=5, pady=10)

        btn_filtrar_fecha = ctk.CTkButton(
            filter_frame,
            text="🔍 Filtrar Fecha",
            width=110,
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self.filtrar_por_fecha_manual
        )
        btn_filtrar_fecha.pack(side="left", padx=10, pady=10)

        self.kpi_frame = ctk.CTkFrame(self.scroll_reportes, fg_color="transparent")
        self.kpi_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            self.scroll_reportes, text="💳 Desglose por Forma de Pago", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", pady=(10, 5))

        self.frame_pagos_desglose = ctk.CTkFrame(self.scroll_reportes, fg_color="#1e293b")
        self.frame_pagos_desglose.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            self.scroll_reportes, text="📋 Historial Detallado de Órdenes y Usuarios", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", pady=(10, 5))

        self.frame_tabla_pedidos = ctk.CTkFrame(self.scroll_reportes, fg_color="#1e293b")
        self.frame_tabla_pedidos.pack(fill="both", expand=True)

        self.actualizar_reportes()

    def al_cambiar_opcion_filtro(self, opcion):
        if opcion != "Día Específico":
            self.actualizar_reportes()

    def filtrar_por_fecha_manual(self):
        self.combo_filtro_fecha.set("Día Específico")
        self.actualizar_reportes()

    def actualizar_reportes(self):
        opcion = self.combo_filtro_fecha.get()
        hoy = datetime.now()
        filtro_sql = ""

        if opcion == "Hoy":
            filtro_sql = f"WHERE fecha_hora LIKE '{hoy.strftime('%Y-%m-%d')}%'"
        elif opcion == "Ayer":
            filtro_sql = f"WHERE fecha_hora LIKE '{(hoy - timedelta(days=1)).strftime('%Y-%m-%d')}%'"
        elif opcion == "Últimos 7 días":
            filtro_sql = f"WHERE fecha_hora >= '{(hoy - timedelta(days=7)).strftime('%Y-%m-%d')}'"
        elif opcion == "Día Específico":
            fecha_manual = self.entry_fecha_especifica.get().strip()
            if fecha_manual:
                filtro_sql = f"WHERE fecha_hora LIKE '{fecha_manual}%'"

        for w in self.kpi_frame.winfo_children():
            w.destroy()

        and_cobrado = "AND estado='cobrado'" if filtro_sql else "WHERE estado='cobrado'"
        self.cursor.execute(f"SELECT SUM(total) FROM pedidos {filtro_sql} {and_cobrado}")
        total_cobrado = self.cursor.fetchone()[0] or 0.0

        card_total = ctk.CTkFrame(self.kpi_frame, fg_color="#1e293b", border_width=1, border_color="#10b981")
        card_total.pack(side="left", fill="both", expand=True, padx=5)
        ctk.CTkLabel(card_total, text="💵 Ventas Totales Cobradas", font=ctk.CTkFont(size=13)).pack(pady=(10, 2))
        ctk.CTkLabel(card_total, text=f"${total_cobrado:.2f}", font=ctk.CTkFont(size=22, weight="bold"), text_color="#10b981").pack(pady=(0, 10))

        self.cursor.execute(f"SELECT COUNT(*) FROM pedidos {filtro_sql}")
        total_pedidos = self.cursor.fetchone()[0] or 0
        card_pedidos = ctk.CTkFrame(self.kpi_frame, fg_color="#1e293b", border_width=1, border_color="#38bdf8")
        card_pedidos.pack(side="left", fill="both", expand=True, padx=5)
        ctk.CTkLabel(card_pedidos, text="📦 Cantidad de Pedidos", font=ctk.CTkFont(size=13)).pack(pady=(10, 2))
        ctk.CTkLabel(card_pedidos, text=str(total_pedidos), font=ctk.CTkFont(size=22, weight="bold"), text_color="#38bdf8").pack(pady=(0, 10))

        for w in self.frame_pagos_desglose.winfo_children():
            w.destroy()

        self.cursor.execute("SELECT nombre FROM metodos_pago")
        metodos = [m[0] for m in self.cursor.fetchall()]

        grid_pagos = ctk.CTkFrame(self.frame_pagos_desglose, fg_color="transparent")
        grid_pagos.pack(fill="x", padx=10, pady=10)

        for idx, mp in enumerate(metodos):
            cond_mp = f"{filtro_sql} AND estado='cobrado' AND metodo_pago='{mp}'" if filtro_sql else f"WHERE estado='cobrado' AND metodo_pago='{mp}'"
            self.cursor.execute(f"SELECT SUM(total), COUNT(*) FROM pedidos {cond_mp}")
            res_mp = self.cursor.fetchone()
            subtotal_mp = res_mp[0] or 0.0
            cant_mp = res_mp[1] or 0

            col = idx % 3
            row = idx // 3

            box = ctk.CTkFrame(grid_pagos, fg_color="#0f172a", corner_radius=8)
            box.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            grid_pagos.grid_columnconfigure(col, weight=1)

            ctk.CTkLabel(box, text=mp, font=ctk.CTkFont(size=12, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=10, pady=(8, 2))
            ctk.CTkLabel(box, text=f"${subtotal_mp:.2f}  ({cant_mp} transacc.)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#10b981").pack(anchor="w", padx=10, pady=(0, 8))

        for w in self.frame_tabla_pedidos.winfo_children():
            w.destroy()

        header_row = ctk.CTkFrame(self.frame_tabla_pedidos, fg_color="#334155")
        header_row.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(header_row, text="ID", width=40, font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="left", padx=5)
        # Se amplió el ancho a 150 para que quepan la Fecha y la Hora cómodamente
        ctk.CTkLabel(header_row, text="Fecha y Hora", width=150, font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_row, text="Tomado por (Usuario)", width=130, font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_row, text="Cliente/Mesa", width=110, font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_row, text="Forma de Pago", width=140, font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_row, text="Total", width=70, font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_row, text="Estado", width=90, font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="left", padx=5)

        self.cursor.execute(f"SELECT id, cliente, items, total, estado, mesero, metodo_pago, fecha_hora FROM pedidos {filtro_sql} ORDER BY id DESC")
        for p_id, cliente, items_raw, total, estado, mesero, mp, fh in self.cursor.fetchall():
            f_row = ctk.CTkFrame(self.frame_tabla_pedidos, fg_color="#0f172a")
            f_row.pack(fill="x", padx=5, pady=3)

            # CORRECCIÓN AQUÍ: Se muestra la cadena completa 'YYYY-MM-DD HH:MM' en lugar de recortar solo la hora
            fecha_f = fh[:16] if len(fh) >= 16 else (fh if fh else "N/A")

            ctk.CTkLabel(f_row, text=f"#{p_id}", width=40, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(f_row, text=fecha_f, width=150, font=ctk.CTkFont(size=11), text_color="gray70", anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(f_row, text=mesero, width=130, font=ctk.CTkFont(weight="bold"), text_color="#10b981", anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(f_row, text=cliente, width=110, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(f_row, text=mp if mp else "Efectivo", width=140, text_color="#38bdf8", anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(f_row, text=f"${total:.2f}", width=70, font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="left", padx=5)

            color_est = "#10b981" if estado == "cobrado" else "#38bdf8"
            if estado == "anulado":
                color_est = "#ef4444"

            ctk.CTkLabel(f_row, text=estado.upper(), width=90, text_color=color_est, font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="left", padx=5)

    # ==========================================
    # MÓDULO DE PEDIDOS
    # ==========================================
    def vista_mesero(self):
        self.construir_modulo_pedido(self.main_container)

    def construir_modulo_pedido(self, parent_frame, es_multitarea=False):
        left_p = ctk.CTkFrame(parent_frame, corner_radius=12)
        left_p.pack(side="left", fill="both", expand=True, padx=(0, 10))

        top_bar = ctk.CTkFrame(left_p, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(top_bar, text="📁 Secciones:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))

        self.cursor.execute("SELECT nombre FROM categorias")
        cats = ["Todas"] + [c[0] for c in self.cursor.fetchall()]

        self.combo_cat_filtro = ctk.CTkOptionMenu(
            top_bar,
            values=cats,
            command=lambda cat: self.cargar_tarjetas_productos(cat),
        )
        self.combo_cat_filtro.pack(side="left")

        self.scroll_menu = ctk.CTkScrollableFrame(left_p, fg_color="transparent")
        self.scroll_menu.pack(fill="both", expand=True, padx=10, pady=10)

        right_p = ctk.CTkFrame(parent_frame, width=380, corner_radius=12)
        right_p.pack(side="right", fill="y", padx=(10, 0))

        ctk.CTkLabel(right_p, text="Orden del Cliente", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=15, pady=10)

        self.entry_cliente = ctk.CTkEntry(right_p, placeholder_text="Cliente / Mesa", height=40, corner_radius=8)
        self.entry_cliente.pack(fill="x", padx=15, pady=(0, 10))

        porciones_frame = ctk.CTkFrame(right_p, fg_color="#1e293b", corner_radius=8)
        porciones_frame.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            porciones_frame, text="🍟 Porciones Rápidas:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38bdf8"
        ).pack(anchor="w", padx=10, pady=(5, 3))

        btn_porciones_grid = ctk.CTkFrame(porciones_frame, fg_color="transparent")
        btn_porciones_grid.pack(fill="x", padx=5, pady=(0, 5))

        self.cursor.execute(
            "SELECT nombre, precio, requiere_salsa FROM productos WHERE categoria LIKE '%Porción%' OR categoria LIKE '%Acompañante%'"
        )
        porciones = self.cursor.fetchall()
        if not porciones:
            porciones = [("Papas", 1.50, 0), ("Arroz", 1.00, 0), ("Ensalada", 1.25, 0)]

        for idx, tuple_p in enumerate(porciones[:4]):
            p_nom, p_pre = tuple_p[0], tuple_p[1]
            p_req = tuple_p[2] if len(tuple_p) > 2 else 0

            col = idx % 2
            row = idx // 2
            btn_porc = ctk.CTkButton(
                btn_porciones_grid,
                text=f"+ {p_nom} (${p_pre:.2f})",
                font=ctk.CTkFont(size=11),
                fg_color="#334155",
                hover_color="#0284c7",
                height=26,
                command=lambda n=p_nom, p=p_pre, req=p_req: self.procesar_agregar_producto(n, p, req),
            )
            btn_porc.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            btn_porciones_grid.grid_columnconfigure(col, weight=1)

        btn_item_libre = ctk.CTkButton(
            right_p,
            text="✨ + Item Especial / Pedido Libre",
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            font=ctk.CTkFont(weight="bold"),
            command=self.dialogo_item_libre,
        )
        btn_item_libre.pack(fill="x", padx=15, pady=(0, 10))

        self.frame_carrito_items = ctk.CTkScrollableFrame(right_p, height=220, fg_color="#0f172a")
        self.frame_carrito_items.pack(fill="both", expand=True, padx=15, pady=5)

        self.lbl_total_mesero = ctk.CTkLabel(
            right_p, text="TOTAL: $0.00", font=ctk.CTkFont(size=18, weight="bold"), text_color="#10b981"
        )
        self.lbl_total_mesero.pack(anchor="e", padx=15, pady=10)

        btn_enviar = ctk.CTkButton(
            right_p,
            text="🚀 REGISTRAR PEDIDO",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=45,
            corner_radius=10,
            command=self.enviar_pedido,
        )
        btn_enviar.pack(fill="x", padx=15, pady=15)

        self.cargar_tarjetas_productos("Todas")

    def procesar_agregar_producto(self, nombre, precio, requiere_salsa):
        if requiere_salsa == 1:
            self.solicitar_opciones_producto(nombre, precio)
        else:
            self.agregar_al_carrito(nombre, precio)

    def solicitar_opciones_producto(self, nombre, precio):
        self.cursor.execute("SELECT nombre FROM salsas")
        salsas_bd = [s[0] for s in self.cursor.fetchall()]
        if not salsas_bd:
            salsas_bd = ["BBQ", "Picante", "Sin Salsa / Al Natural"]

        ventana_salsa = ctk.CTkToplevel(self)
        ventana_salsa.title(f"Salsa / Opciones - {nombre}")
        ventana_salsa.geometry("420x330")
        ventana_salsa.grab_set()

        ctk.CTkLabel(
            ventana_salsa,
            text=f"🍗 Opciones para:\n{nombre}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8",
        ).pack(pady=(15, 10))

        ctk.CTkLabel(
            ventana_salsa, text="Selecciona la Salsa Registrada:", font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=30, pady=(5, 2))

        combo_salsa = ctk.CTkOptionMenu(ventana_salsa, values=salsas_bd, width=360, height=35)
        combo_salsa.pack(pady=5)

        ctk.CTkLabel(
            ventana_salsa, text="Nota Adicional (Opcional):", font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=30, pady=(10, 2))

        entry_nota = ctk.CTkEntry(
            ventana_salsa, placeholder_text="Ej: Salsa aparte, bien crujiente, etc.", width=360, height=35
        )
        entry_nota.pack(pady=5)

        def agregar():
            salsa_sel = combo_salsa.get()
            nota_extra = entry_nota.get().strip()

            detalle_final = f"{nombre} [{salsa_sel}]"
            if nota_extra:
                detalle_final += f" ({nota_extra})"

            self.agregar_al_carrito(detalle_final, precio)
            ventana_salsa.destroy()

        btn_confirmar = ctk.CTkButton(
            ventana_salsa,
            text="✔ Agregar al Carrito",
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(weight="bold"),
            height=40,
            command=agregar,
        )
        btn_confirmar.pack(pady=20)

    def dialogo_item_libre(self):
        dialogo = ctk.CTkToplevel(self)
        dialogo.title("Agregar Pedido Especial / Libre")
        dialogo.geometry("400x260")
        dialogo.grab_set()

        ctk.CTkLabel(dialogo, text="📝 Detalle del Pedido Libre", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15)

        entry_desc = ctk.CTkEntry(dialogo, placeholder_text="Descripción del Pedido Especial", width=320, height=40)
        entry_desc.pack(pady=5)

        entry_precio = ctk.CTkEntry(dialogo, placeholder_text="Precio Final ($)", width=320, height=40)
        entry_precio.pack(pady=10)

        def agregar():
            desc = entry_desc.get().strip()
            p_str = entry_precio.get().strip()
            if not desc or not p_str:
                return messagebox.showwarning("Atención", "Ingresa la descripción y el precio.")
            try:
                precio = float(p_str)
                self.agregar_al_carrito(f"⭐ {desc}", precio)
                dialogo.destroy()
            except ValueError:
                messagebox.showerror("Error", "El precio ingresado no es válido.")

        ctk.CTkButton(dialogo, text="Agregar a la Cuenta", fg_color="#8b5cf6", command=agregar).pack(pady=10)

    def cargar_tarjetas_productos(self, categoria="Todas"):
        for w in self.scroll_menu.winfo_children():
            w.destroy()

        if categoria == "Todas":
            self.cursor.execute("SELECT nombre, precio, icono, imagen_path, requiere_salsa FROM productos")
        else:
            self.cursor.execute(
                "SELECT nombre, precio, icono, imagen_path, requiere_salsa FROM productos WHERE categoria=?",
                (categoria,),
            )

        prods = self.cursor.fetchall()

        for i, (nombre, precio, icono, img_path, req_salsa) in enumerate(prods):
            row = i // 3
            col = i % 3

            card = ctk.CTkFrame(self.scroll_menu, corner_radius=10, fg_color="#1e293b")
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

            if img_path and os.path.exists(img_path):
                try:
                    my_img = ctk.CTkImage(
                        light_image=Image.open(img_path),
                        dark_image=Image.open(img_path),
                        size=(90, 70),
                    )
                    ctk.CTkLabel(card, image=my_img, text="").pack(pady=(10, 5))
                except:
                    ctk.CTkLabel(card, text=icono, font=ctk.CTkFont(size=35)).pack(pady=(12, 2))
            else:
                ctk.CTkLabel(card, text=icono, font=ctk.CTkFont(size=35)).pack(pady=(12, 2))

            ctk.CTkLabel(card, text=nombre, font=ctk.CTkFont(size=13, weight="bold")).pack()
            ctk.CTkLabel(
                card, text=f"${precio:.2f}", font=ctk.CTkFont(size=13), text_color="#10b981"
            ).pack(pady=(0, 10))

            btn_add = ctk.CTkButton(
                card,
                text="Agregar +",
                width=120,
                height=28,
                fg_color="#334155",
                hover_color="#10b981",
                command=lambda n=nombre, p=precio, req=req_salsa: self.procesar_agregar_producto(n, p, req),
            )
            btn_add.pack(pady=(0, 12))

    def agregar_al_carrito(self, nombre, precio):
        self.carrito.append({"nombre": nombre, "precio": precio})
        self.actualizar_carrito_ui()

    def actualizar_carrito_ui(self):
        for widget in self.frame_carrito_items.winfo_children():
            widget.destroy()

        total = 0.0
        for idx, item in enumerate(self.carrito):
            total += item["precio"]

            row = ctk.CTkFrame(self.frame_carrito_items, height=35, fg_color="#1e293b")
            row.pack(fill="x", pady=3, padx=2)

            ctk.CTkLabel(row, text=item["nombre"], font=ctk.CTkFont(size=12)).pack(side="left", padx=10)
            ctk.CTkLabel(
                row,
                text=f"${item['precio']:.2f}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#10b981",
            ).pack(side="left", padx=5)

            btn_del = ctk.CTkButton(
                row,
                text="✕",
                width=25,
                height=22,
                fg_color="#ef4444",
                hover_color="#dc2626",
                command=lambda i=idx: self.quitar_del_carrito(i),
            )
            btn_del.pack(side="right", padx=5)

        self.lbl_total_mesero.configure(text=f"TOTAL: ${total:.2f}")

    def quitar_del_carrito(self, idx):
        self.carrito.pop(idx)
        self.actualizar_carrito_ui()

    def enviar_pedido(self):
        cliente = self.entry_cliente.get().strip()
        if not cliente or not self.carrito:
            return messagebox.showwarning("Atención", "Escribe el nombre del cliente y agrega productos.")

        total = sum(i["precio"] for i in self.carrito)
        items_json = json.dumps(self.carrito)
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.cursor.execute(
            "INSERT INTO pedidos (cliente, items, total, mesero, fecha_hora) VALUES (?, ?, ?, ?, ?)",
            (cliente, items_json, total, self.usuario_actual, fecha_actual),
        )
        self.conn.commit()

        self.carrito.clear()
        self.entry_cliente.delete(0, "end")
        self.actualizar_carrito_ui()
        messagebox.showinfo("Éxito", "¡Orden registrada correctamente!")

    # ==========================================
    # GESTIÓN DE MENÚ EN ADMIN
    # ==========================================
    def vista_gestion_menu(self):
        for w in self.container_menu_admin.winfo_children():
            w.destroy()

        left_col = ctk.CTkFrame(self.container_menu_admin, width=380, corner_radius=12)
        left_col.pack(side="left", fill="y", padx=(0, 10), pady=5)

        ctk.CTkLabel(left_col, text="📁 Gestor de Secciones", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(15, 5), padx=15, anchor="w")

        f_sec = ctk.CTkFrame(left_col, fg_color="transparent")
        f_sec.pack(fill="x", padx=15, pady=5)

        self.entry_nueva_sec = ctk.CTkEntry(f_sec, placeholder_text="Nueva Sección", width=190)
        self.entry_nueva_sec.pack(side="left", padx=(0, 5))

        btn_add_sec = ctk.CTkButton(f_sec, text="+ Crear", width=70, fg_color="#10b981", command=self.crear_seccion)
        btn_add_sec.pack(side="left")

        f_del_sec = ctk.CTkFrame(left_col, fg_color="transparent")
        f_del_sec.pack(fill="x", padx=15, pady=(5, 10))

        self.combo_del_sec = ctk.CTkOptionMenu(f_del_sec, values=["General"], width=190)
        self.combo_del_sec.pack(side="left", padx=(0, 5))

        btn_del_sec = ctk.CTkButton(
            f_del_sec, text="🗑 Borrar", width=70, fg_color="#ef4444", hover_color="#dc2626", command=self.eliminar_seccion
        )
        btn_del_sec.pack(side="left")

        ctk.CTkFrame(left_col, height=2, fg_color="#334155").pack(fill="x", pady=10, padx=15)

        ctk.CTkLabel(left_col, text="➕ Registrar Producto", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(5, 10), padx=15, anchor="w")

        self.entry_nom_prod = ctk.CTkEntry(left_col, placeholder_text="Nombre del Producto", height=38)
        self.entry_nom_prod.pack(fill="x", padx=15, pady=5)

        self.entry_precio_prod = ctk.CTkEntry(left_col, placeholder_text="Precio (ej: 4.50)", height=38)
        self.entry_precio_prod.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(left_col, text="Asignar a Sección:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=15, pady=(5,0))
        self.combo_secciones_prod = ctk.CTkOptionMenu(left_col, values=["General"])
        self.combo_secciones_prod.pack(fill="x", padx=15, pady=5)

        self.chk_requiere_salsa = ctk.CTkCheckBox(
            left_col, text="¿Requiere elegir salsa / término?", font=ctk.CTkFont(size=12), text_color="#38bdf8"
        )
        self.chk_requiere_salsa.pack(anchor="w", padx=15, pady=8)

        self.btn_select_img = ctk.CTkButton(
            left_col, text="📷 Seleccionar Imagen", fg_color="#334155", hover_color="#475569", command=self.seleccionar_imagen_producto
        )
        self.btn_select_img.pack(fill="x", padx=15, pady=5)

        self.lbl_path_img = ctk.CTkLabel(left_col, text="Sin imagen seleccionada", font=ctk.CTkFont(size=11))
        self.lbl_path_img.pack(padx=15, pady=(0, 5))

        btn_guardar_prod = ctk.CTkButton(
            left_col, text="💾 GUARDAR EN EL MENÚ", fg_color="#10b981", font=ctk.CTkFont(weight="bold"), height=40, command=self.guardar_producto_menu
        )
        btn_guardar_prod.pack(fill="x", padx=15, pady=10)

        list_frame = ctk.CTkFrame(self.container_menu_admin, corner_radius=12)
        list_frame.pack(side="right", fill="both", expand=True, pady=5)

        ctk.CTkLabel(list_frame, text="📋 Menú de Productos", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15, padx=15, anchor="w")

        self.scroll_lista_menu = ctk.CTkScrollableFrame(list_frame, fg_color="transparent")
        self.scroll_lista_menu.pack(fill="both", expand=True, padx=10, pady=10)

        self.actualizar_secciones_combo()
        self.actualizar_lista_menu_admin()

    def crear_seccion(self):
        nombre = self.entry_nueva_sec.get().strip()
        if not nombre:
            return
        try:
            self.cursor.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
            self.conn.commit()
            self.entry_nueva_sec.delete(0, "end")
            self.actualizar_secciones_combo()
            messagebox.showinfo("Éxito", f"Sección '{nombre}' creada.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "La sección ya existe.")

    def eliminar_seccion(self):
        seccion = self.combo_del_sec.get()
        if seccion == "General":
            return messagebox.showwarning("Atención", "No se puede eliminar la sección predeterminada 'General'.")

        if messagebox.askyesno("Confirmar Eliminación", f"¿Deseas eliminar la sección '{seccion}'?\nLos productos se moverán a 'General'."):
            self.cursor.execute("UPDATE productos SET categoria = 'General' WHERE categoria = ?", (seccion,))
            self.cursor.execute("DELETE FROM categorias WHERE nombre = ?", (seccion,))
            self.conn.commit()
            self.actualizar_secciones_combo()
            self.actualizar_lista_menu_admin()
            messagebox.showinfo("Éxito", f"Sección '{seccion}' eliminada.")

    def actualizar_secciones_combo(self):
        self.cursor.execute("SELECT nombre FROM categorias")
        cats = [c[0] for c in self.cursor.fetchall()]
        if hasattr(self, 'combo_secciones_prod'):
            self.combo_secciones_prod.configure(values=cats)
        if hasattr(self, 'combo_del_sec'):
            self.combo_del_sec.configure(values=[c for c in cats if c != "General"])

    def seleccionar_imagen_producto(self):
        archivo = filedialog.askopenfilename(
            title="Selecciona la foto del producto",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp")],
        )
        if archivo:
            self.ruta_imagen_seleccionada = archivo
            nom = os.path.basename(archivo)
            self.lbl_path_img.configure(text=f"Cargado: {nom[:20]}...", text_color="#10b981")

    def guardar_producto_menu(self):
        nombre = self.entry_nom_prod.get().strip()
        precio_str = self.entry_precio_prod.get().strip()
        categoria = self.combo_secciones_prod.get()
        req_salsa = 1 if self.chk_requiere_salsa.get() == 1 else 0

        if not nombre or not precio_str:
            return messagebox.showwarning("Atención", "Ingresa el nombre y el precio.")

        try:
            precio = float(precio_str)
        except ValueError:
            return messagebox.showerror("Error", "El precio debe ser un número válido.")

        dest_path = ""
        if self.ruta_imagen_seleccionada:
            try:
                ext = os.path.splitext(self.ruta_imagen_seleccionada)[1]
                nom_limpio = "".join(c for c in nombre if c.isalnum() or c in (" ", "_")).rstrip()
                dest_path = os.path.join("imagenes", f"prod_{nom_limpio.replace(' ', '_')}{ext}")

                with Image.open(self.ruta_imagen_seleccionada) as img:
                    img_rgb = img.convert("RGB")
                    img_rgb.save(dest_path)
            except Exception as e:
                dest_path = ""

        try:
            self.cursor.execute(
                "INSERT INTO productos (nombre, precio, categoria, icono, imagen_path, requiere_salsa) VALUES (?, ?, ?, ?, ?, ?)",
                (nombre, precio, categoria, "🍔", dest_path, req_salsa),
            )
            self.conn.commit()

            self.entry_nom_prod.delete(0, "end")
            self.entry_precio_prod.delete(0, "end")
            self.chk_requiere_salsa.deselect()
            self.ruta_imagen_seleccionada = None
            self.lbl_path_img.configure(text="Sin imagen seleccionada", text_color="gray")

            messagebox.showinfo("Éxito", f"¡Producto '{nombre}' guardado!")
            self.actualizar_lista_menu_admin()
        except Exception as err_db:
            messagebox.showerror("Error DB", f"Error en base de datos: {err_db}")

    def actualizar_lista_menu_admin(self):
        for w in self.scroll_lista_menu.winfo_children():
            w.destroy()

        self.cursor.execute("SELECT id, nombre, precio, categoria, requiere_salsa FROM productos")
        prods = self.cursor.fetchall()

        for p_id, nombre, precio, cat, req_salsa in prods:
            row = ctk.CTkFrame(self.scroll_lista_menu, fg_color="#1e293b", height=50)
            row.pack(fill="x", pady=4, padx=5)

            ctk.CTkLabel(row, text=nombre, font=ctk.CTkFont(weight="bold"), width=180, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=f"[{cat}]", text_color="gray70", width=120, anchor="w").pack(side="left", padx=5)
            
            salsa_lbl = " [Salsa Activa]" if req_salsa == 1 else ""
            ctk.CTkLabel(row, text=f"${precio:.2f}{salsa_lbl}", text_color="#10b981", font=ctk.CTkFont(weight="bold"), width=120, anchor="w").pack(side="left", padx=5)

            btn_del = ctk.CTkButton(
                row, text="🗑 Eliminar", width=80, height=28, fg_color="#ef4444", command=lambda id_p=p_id: self.eliminar_producto_menu(id_p)
            )
            btn_del.pack(side="right", padx=10)

    def eliminar_producto_menu(self, p_id):
        if messagebox.askyesno("Confirmar", "¿Seguro que deseas eliminar este producto?"):
            self.cursor.execute("DELETE FROM productos WHERE id = ?", (p_id,))
            self.conn.commit()
            self.actualizar_lista_menu_admin()

    # ==========================================
    # FORMAS DE PAGO Y CAJA
    # ==========================================
    def vista_gestion_metodos_pago(self):
        for w in self.container_pagos_admin.winfo_children():
            w.destroy()

        f_left = ctk.CTkFrame(self.container_pagos_admin, width=350)
        f_left.pack(side="left", fill="y", padx=10, pady=10)

        ctk.CTkLabel(f_left, text="💳 Añadir Forma de Pago", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15, padx=15)

        self.entry_nuevo_metodo = ctk.CTkEntry(f_left, placeholder_text="Ej: Tarjeta de Crédito", height=40)
        self.entry_nuevo_metodo.pack(fill="x", padx=15, pady=10)

        btn_guardar_mp = ctk.CTkButton(f_left, text="Guardar Método", fg_color="#10b981", command=self.guardar_metodo_pago)
        btn_guardar_mp.pack(fill="x", padx=15, pady=10)

        f_right = ctk.CTkFrame(self.container_pagos_admin)
        f_right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(f_right, text="📋 Métodos de Pago Activos", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15, padx=15)

        self.scroll_metodos_pago = ctk.CTkScrollableFrame(f_right, fg_color="transparent")
        self.scroll_metodos_pago.pack(fill="both", expand=True, padx=15, pady=10)

        self.actualizar_lista_metodos_pago()

    def guardar_metodo_pago(self):
        nombre = self.entry_nuevo_metodo.get().strip()
        if not nombre:
            return
        try:
            self.cursor.execute("INSERT INTO metodos_pago (nombre) VALUES (?)", (nombre,))
            self.conn.commit()
            self.entry_nuevo_metodo.delete(0, "end")
            self.actualizar_lista_metodos_pago()
            messagebox.showinfo("Éxito", f"Método de pago '{nombre}' agregado.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Este método de pago ya existe.")

    def actualizar_lista_metodos_pago(self):
        for w in self.scroll_metodos_pago.winfo_children():
            w.destroy()

        self.cursor.execute("SELECT id, nombre FROM metodos_pago")
        for m_id, nom in self.cursor.fetchall():
            row = ctk.CTkFrame(self.scroll_metodos_pago, fg_color="#1e293b", height=40)
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(row, text=nom, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15)

            btn_del = ctk.CTkButton(row, text="🗑", width=30, fg_color="#ef4444", command=lambda i=m_id: self.eliminar_metodo_pago(i))
            btn_del.pack(side="right", padx=10)

    def eliminar_metodo_pago(self, m_id):
        self.cursor.execute("DELETE FROM metodos_pago WHERE id = ?", (m_id,))
        self.conn.commit()
        self.actualizar_lista_metodos_pago()

    def vista_caja(self):
        self.construir_modulo_caja(self.main_container)

    def construir_modulo_caja(self, parent_frame):
        for w in parent_frame.winfo_children():
            w.destroy()

        self.cursor.execute("SELECT id, monto_apertura FROM cajas WHERE cajero=? AND estado='abierta'", (self.usuario_actual,))
        caja_abierta = self.cursor.fetchone()

        bar_caja = ctk.CTkFrame(parent_frame, height=50, fg_color="#1e293b")
        bar_caja.pack(fill="x", pady=(0, 10))

        if not caja_abierta:
            ctk.CTkLabel(bar_caja, text="⚠️ CAJA CERRADA", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ef4444").pack(side="left", padx=15)
            btn_abrir = ctk.CTkButton(bar_caja, text="🔓 ABRIR CAJA", fg_color="#10b981", command=lambda: self.dialogo_abrir_caja(parent_frame))
            btn_abrir.pack(side="left", padx=10)
        else:
            ctk.CTkLabel(
                bar_caja, text=f"🟢 CAJA ABIERTA (Base: ${caja_abierta[1]:.2f})", font=ctk.CTkFont(size=14, weight="bold"), text_color="#10b981"
            ).pack(side="left", padx=15)
            btn_cerrar = ctk.CTkButton(
                bar_caja, text="🔒 CERRAR CAJA", fg_color="#ef4444", command=lambda: self.dialogo_cerrar_caja(caja_abierta[0], parent_frame)
            )
            btn_cerrar.pack(side="right", padx=15)

        self.scroll_caja = ctk.CTkScrollableFrame(parent_frame, fg_color="transparent")
        self.scroll_caja.pack(fill="both", expand=True)
        self.actualizar_caja()

    def dialogo_abrir_caja(self, parent_frame):
        dialogo = ctk.CTkInputDialog(text="Ingresa el monto base en caja ($):", title="Apertura de Caja")
        monto_str = dialogo.get_input()

        if monto_str is not None:
            try:
                monto = float(monto_str)
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cursor.execute(
                    "INSERT INTO cajas (cajero, monto_apertura, fecha_apertura, estado) VALUES (?, ?, ?, 'abierta')",
                    (self.usuario_actual, monto, fecha),
                )
                self.conn.commit()
                messagebox.showinfo("Éxito", f"Caja abierta con ${monto:.2f}")
                self.construir_modulo_caja(parent_frame)
            except ValueError:
                messagebox.showerror("Error", "Monto no válido.")

    def dialogo_cerrar_caja(self, caja_id, parent_frame):
        self.cursor.execute("SELECT SUM(total) FROM pedidos WHERE estado='cobrado'")
        total_ventas = self.cursor.fetchone()[0] or 0.0

        self.cursor.execute("SELECT monto_apertura FROM cajas WHERE id=?", (caja_id,))
        base = self.cursor.fetchone()[0]

        esperado = base + total_ventas

        if messagebox.askyesno(
            "Cierre de Caja",
            f"📊 RESUMEN:\n\n• Base Inicial: ${base:.2f}\n• Ventas Cobradas: ${total_ventas:.2f}\n• TOTAL ESPERADO: ${esperado:.2f}\n\n¿Cerrar caja?",
        ):
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "UPDATE cajas SET monto_cierre=?, ventas_efectivo=?, fecha_cierre=?, estado='cerrada' WHERE id=?",
                (esperado, total_ventas, fecha, caja_id),
            )
            self.conn.commit()
            messagebox.showinfo("Caja Cerrada", f"Arqueo final: ${esperado:.2f}")
            self.construir_modulo_caja(parent_frame)

    def actualizar_caja(self):
        for widget in self.scroll_caja.winfo_children():
            widget.destroy()

        self.cursor.execute("SELECT nombre FROM metodos_pago")
        metodos = [m[0] for m in self.cursor.fetchall()]

        self.cursor.execute(
            "SELECT id, cliente, items, total, estado, mesero, fecha_hora FROM pedidos WHERE estado != 'cobrado' AND estado != 'anulado'"
        )
        pedidos = self.cursor.fetchall()

        for i, (p_id, cliente, items_raw, total, estado, mesero, fh) in enumerate(pedidos):
            row = i // 3
            col = i % 3

            card = ctk.CTkFrame(self.scroll_caja, corner_radius=12, fg_color="#1e293b", border_width=1, border_color="#38bdf8")
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            ctk.CTkLabel(card, text=f"Orden #{p_id} - {cliente}", font=ctk.CTkFont(size=15, weight="bold"), text_color="#38bdf8").pack(pady=(5, 2), padx=15, anchor="w")
            ctk.CTkLabel(card, text=f"Atendido: {mesero}", font=ctk.CTkFont(size=11), text_color="gray70").pack(padx=15, anchor="w")

            btn_add_item = ctk.CTkButton(
                card, text="➕ Añadir Adicional", width=120, height=24, fg_color="#334155", command=lambda id_p=p_id, it=items_raw, tot=total: self.agregar_item_desde_caja(id_p, it, tot)
            )
            btn_add_item.pack(anchor="e", padx=15, pady=(5, 0))

            ctk.CTkLabel(card, text=f"Total: ${total:.2f}", font=ctk.CTkFont(size=20, weight="bold"), text_color="#10b981").pack(pady=5)

            combo_pago = ctk.CTkOptionMenu(card, values=metodos)
            combo_pago.pack(fill="x", padx=10, pady=3)

            btn_cobrar = ctk.CTkButton(
                card, text="💵 COBRAR", fg_color="#0284c7", font=ctk.CTkFont(weight="bold"), command=lambda id_p=p_id, t=total, mp=combo_pago: self.procesar_cobro_metodo(id_p, t, mp.get())
            )
            btn_cobrar.pack(fill="x", padx=10, pady=(5, 10))

    def agregar_item_desde_caja(self, pedido_id, items_json_actual, total_actual):
        self.cursor.execute("SELECT nombre, precio FROM productos")
        productos = self.cursor.fetchall()

        ventana_add = ctk.CTkToplevel(self)
        ventana_add.title(f"Añadir Adicional - Orden #{pedido_id}")
        ventana_add.geometry("400x220")
        ventana_add.grab_set()

        nombres_prods = [f"{p[0]} - ${p[1]:.2f}" for p in productos]
        combo_prods = ctk.CTkOptionMenu(ventana_add, values=nombres_prods, width=280)
        combo_prods.pack(pady=20)

        def confirmar():
            seleccion = combo_prods.get()
            for nombre, precio in productos:
                if f"{nombre} - ${precio:.2f}" == seleccion:
                    items_lista = json.loads(items_json_actual)
                    items_lista.append({"nombre": nombre, "precio": precio})
                    nuevo_total = total_actual + precio
                    self.cursor.execute(
                        "UPDATE pedidos SET items = ?, total = ? WHERE id = ?",
                        (json.dumps(items_lista), nuevo_total, pedido_id),
                    )
                    self.conn.commit()
                    ventana_add.destroy()
                    self.actualizar_caja()
                    break

        ctk.CTkButton(ventana_add, text="Agregar", fg_color="#10b981", command=confirmar).pack(pady=10)

    def procesar_cobro_metodo(self, p_id, total, metodo_pago):
        self.cursor.execute(
            "UPDATE pedidos SET estado = 'cobrado', metodo_pago = ? WHERE id = ?",
            (metodo_pago, p_id),
        )
        self.conn.commit()
        messagebox.showinfo("Éxito", f"Orden #{p_id} cobrada en {metodo_pago}.\nTotal: ${total:.2f}")
        self.actualizar_caja()

    # ==========================================
    # OTROS MÓDULOS
    # ==========================================
    def construir_modulo_lista_pedidos(self, parent_frame):
        for w in parent_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(parent_frame, text="📋 Historial Activo de Pedidos", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(parent_frame, fg_color="#1e293b")
        scroll.pack(fill="both", expand=True)

        self.cursor.execute("SELECT id, cliente, total, estado, metodo_pago FROM pedidos ORDER BY id DESC LIMIT 50")
        for p_id, cliente, total, estado, mp in self.cursor.fetchall():
            row = ctk.CTkFrame(scroll, fg_color="#0f172a")
            row.pack(fill="x", padx=5, pady=4)

            ctk.CTkLabel(row, text=f"#{p_id}", width=40, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=cliente, width=120, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=f"${total:.2f}", width=70, text_color="#10b981", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=estado.upper(), width=90, text_color="#38bdf8", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=f"Pago: {mp}", width=160, text_color="gray70", anchor="w").pack(side="left", padx=5)

    def vista_cocina(self):
        ctk.CTkLabel(self.main_container, text="🔥 Monitor de Cocina - Comandas Pendientes", font=ctk.CTkFont(size=18, weight="bold"), text_color="#f97316").pack(anchor="w", pady=(0, 15))

        self.scroll_cocina = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self.scroll_cocina.pack(fill="both", expand=True)
        self.actualizar_cocina()

    def actualizar_cocina(self):
        for widget in self.scroll_cocina.winfo_children():
            widget.destroy()

        self.cursor.execute("SELECT id, cliente, items FROM pedidos WHERE estado = 'pendiente'")
        for i, (p_id, cliente, items_raw) in enumerate(self.cursor.fetchall()):
            items = json.loads(items_raw)
            row, col = i // 3, i % 3

            card = ctk.CTkFrame(self.scroll_cocina, corner_radius=12, fg_color="#1e293b", border_width=1, border_color="#f97316")
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            ctk.CTkLabel(card, text=f"Orden #{p_id} - {cliente}", font=ctk.CTkFont(size=15, weight="bold"), text_color="#f97316").pack(pady=(10, 2), padx=15, anchor="w")

            list_frame = ctk.CTkFrame(card, fg_color="#0f172a")
            list_frame.pack(fill="both", expand=True, padx=10, pady=5)

            for item in items:
                ctk.CTkLabel(list_frame, text=f"• {item['nombre']}", anchor="w").pack(fill="x", padx=10, pady=2)

            btn_listo = ctk.CTkButton(card, text="✔ MARCAR LISTO", fg_color="#f97316", command=lambda id_p=p_id: self.marcar_listo_cocina(id_p))
            btn_listo.pack(fill="x", padx=10, pady=10)

    def marcar_listo_cocina(self, p_id):
        self.cursor.execute("UPDATE pedidos SET estado = 'preparado' WHERE id = ?", (p_id,))
        self.conn.commit()
        self.actualizar_cocina()

    def vista_gestion_usuarios(self):
        form_u = ctk.CTkFrame(self.container_usuarios, width=360, corner_radius=12)
        form_u.pack(side="left", fill="y", padx=(0, 10), pady=5)

        self.lbl_titulo_form_u = ctk.CTkLabel(form_u, text="➕ Registrar Usuario", font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_titulo_form_u.pack(pady=15, padx=15, anchor="w")

        self.entry_u_nombre = ctk.CTkEntry(form_u, placeholder_text="Nombre Completo", height=40)
        self.entry_u_nombre.pack(fill="x", padx=15, pady=8)

        self.entry_u_user = ctk.CTkEntry(form_u, placeholder_text="Usuario (Login)", height=40)
        self.entry_u_user.pack(fill="x", padx=15, pady=8)

        self.entry_u_clave = ctk.CTkEntry(form_u, placeholder_text="Contraseña", show="*", height=40)
        self.entry_u_clave.pack(fill="x", padx=15, pady=8)

        self.combo_u_rol = ctk.CTkOptionMenu(form_u, values=["mesero", "cocina", "caja", "multitarea", "admin"], height=38)
        self.combo_u_rol.pack(fill="x", padx=15, pady=(5, 12))

        btn_guardar = ctk.CTkButton(form_u, text="💾 GUARDAR", fg_color="#10b981", command=self.guardar_usuario)
        btn_guardar.pack(fill="x", padx=15, pady=8)

        tabla_frame = ctk.CTkFrame(self.container_usuarios, corner_radius=12)
        tabla_frame.pack(side="right", fill="both", expand=True, pady=5)

        self.scroll_tabla_u = ctk.CTkScrollableFrame(tabla_frame, fg_color="transparent")
        self.scroll_tabla_u.pack(fill="both", expand=True, padx=10, pady=10)

        self.actualizar_tabla_usuarios()

    def guardar_usuario(self):
        nombre = self.entry_u_nombre.get().strip()
        user = self.entry_u_user.get().strip()
        clave = self.entry_u_clave.get().strip()
        rol = self.combo_u_rol.get()

        if not nombre or not user or not clave:
            return messagebox.showwarning("Atención", "Completa todos los campos.")

        try:
            self.cursor.execute("INSERT INTO usuarios (nombre, usuario, clave, rol) VALUES (?, ?, ?, ?)", (nombre, user, clave, rol))
            self.conn.commit()
            messagebox.showinfo("Éxito", f"Usuario '{user}' registrado.")
            self.actualizar_tabla_usuarios()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "El usuario ya existe.")

    def actualizar_tabla_usuarios(self):
        for w in self.scroll_tabla_u.winfo_children():
            w.destroy()

        self.cursor.execute("SELECT id, nombre, usuario, rol FROM usuarios")
        for u_id, nombre, user, rol in self.cursor.fetchall():
            f_row = ctk.CTkFrame(self.scroll_tabla_u, fg_color="#0f172a")
            f_row.pack(fill="x", padx=5, pady=3)

            ctk.CTkLabel(f_row, text=nombre, width=150, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(f_row, text=user, width=120, anchor="w", text_color="gray70").pack(side="left", padx=5)
            ctk.CTkLabel(f_row, text=rol.upper(), width=110, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)

            if u_id != self.user_id_actual:
                btn_del = ctk.CTkButton(f_row, text="🗑 Eliminar", width=75, fg_color="#ef4444", command=lambda i=u_id: self.eliminar_usuario(i))
                btn_del.pack(side="right", padx=5)

    def eliminar_usuario(self, u_id):
        self.cursor.execute("DELETE FROM usuarios WHERE id = ?", (u_id,))
        self.conn.commit()
        self.actualizar_tabla_usuarios()

if __name__ == "__main__":
    app = SistemaPOSPro()
    app.mainloop()
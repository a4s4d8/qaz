import tkinter as tk
from tkinter import ttk, messagebox
import mariadb


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Анализ заказов - ООО 'Молоко'")
        self.root.geometry("1100x650")
        self.root.minsize(900, 500)

        self.conn = None
        self.client_id = None
        self.data = []
        self.highlight = []

        self.create_ui()
        self.connect_db()

    def create_ui(self):
        # Заголовок (упрощенный)
        tk.Label(self.root, text="Анализ заказов - ООО 'Молоко'",
                 font=("Arial", 14, "bold")).pack(fill=tk.X, pady=10)

        # Основная панель
        main = tk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Левая панель
        left = tk.Frame(main, width=250)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Сортировка
        grp = tk.LabelFrame(left, text="Сортировка", padx=10, pady=10)
        grp.pack(fill=tk.X, pady=(0, 10))

        self.sort_field = ttk.Combobox(grp, values=['id_order', 'date_order', 'total_amount', 'client_name'],
                                       state='readonly')
        self.sort_field.set('date_order')
        self.sort_field.pack(fill=tk.X, pady=(0, 10))
        self.sort_field.bind('<<ComboboxSelected>>', lambda e: self.load_orders())

        self.sort_order = tk.StringVar(value="DESC")
        for txt, val in [("По убыванию", "DESC"), ("По возрастанию", "ASC")]:
            tk.Radiobutton(grp, text=txt, variable=self.sort_order, value=val, command=self.load_orders).pack(
                anchor=tk.W)

        # Фильтр
        grp = tk.LabelFrame(left, text="Фильтр по клиенту", padx=10, pady=10)
        grp.pack(fill=tk.X, pady=(0, 10))

        self.client_cb = ttk.Combobox(grp, state='readonly')
        self.client_cb.pack(fill=tk.X, pady=(0, 10))

        btn_frame = tk.Frame(grp)
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="Фильтровать", command=self.apply_filter).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame, text="Показать все", command=self.clear_filter).pack(side=tk.LEFT)

        # Поиск
        grp = tk.LabelFrame(left, text="Поиск", padx=10, pady=10)
        grp.pack(fill=tk.X)

        self.search_entry = tk.Entry(grp)
        self.search_entry.pack(fill=tk.X, pady=(0, 10))
        self.search_entry.bind('<Return>', lambda e: self.search())
        tk.Button(grp, text="Найти", command=self.search).pack(fill=tk.X)

        # Таблица
        right = tk.Frame(main)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        container = tk.Frame(right)
        container.pack(fill=tk.BOTH, expand=True)

        scroll_y = tk.Scrollbar(container)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x = tk.Scrollbar(container, orient=tk.HORIZONTAL)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree = ttk.Treeview(container, yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        # Статус (упрощенный)
        bottom = tk.Frame(self.root, relief=tk.SUNKEN, bd=1)
        bottom.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_count = tk.Label(bottom, text="Заказов: 0")
        self.lbl_count.pack(side=tk.LEFT, padx=10, pady=5)

        self.lbl_sum = tk.Label(bottom, text="Сумма: 0 руб.")
        self.lbl_sum.pack(side=tk.LEFT, padx=10)

        self.lbl_status = tk.Label(bottom, text="")
        self.lbl_status.pack(side=tk.RIGHT, padx=10)

    def connect_db(self):
        try:
            self.conn = mariadb.connect(
                host='192.168.0.176', user='aa', password='12345678', database='milk'
            )
            self.cur = self.conn.cursor(dictionary=True)
            self.load_clients()
            self.load_orders()
            self.status("Подключено")
        except:
            messagebox.showerror("Ошибка", "Нет подключения к БД!")
            self.status("Ошибка подключения")

    def load_clients(self):
        self.cur.execute("SELECT id_customer, name FROM customers WHERE buyer=1 ORDER BY name")
        clients = self.cur.fetchall()
        if clients:
            self.client_cb['values'] = [f"{c['name']} (ID:{c['id_customer']})" for c in clients]

    def load_orders(self):
        try:
            sort = self.sort_field.get()
            order = self.sort_order.get()

            sql = """
                SELECT o.id_order, o.date_order, o.total_amount,
                       c.name as client_name, c.phone as client_phone
                FROM orders_june_2025 o
                LEFT JOIN customers c ON o.id_customer = c.id_customer
            """
            params = []
            if self.client_id:
                sql += " WHERE o.id_customer = %s"
                params.append(self.client_id)

            sort_field = 'c.name' if sort == 'client_name' else f'o.{sort}'
            sql += f" ORDER BY {sort_field} {order}"

            self.cur.execute(sql, params)
            self.data = self.cur.fetchall()
            for r in self.data:
                r['total_amount'] = r['total_amount'] or 0

            self.display()
            self.update_stats()
            self.highlight = []
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не загрузить данные: {e}")

    def display(self):
        self.tree.delete(*self.tree.get_children())
        if not self.data: return

        cols = ['id_order', 'date_order', 'client_name', 'client_phone', 'total_amount']
        heads = ['№ заказа', 'Дата', 'Клиент', 'Телефон', 'Сумма']

        self.tree['columns'] = cols
        self.tree['show'] = 'headings'
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=150 if c == 'client_name' else 100)

        for i, r in enumerate(self.data):
            vals = [
                r['id_order'],
                r['date_order'].strftime('%Y-%m-%d') if r['date_order'] else '',
                r['client_name'] or '',
                r['client_phone'] or '',
                f"{r['total_amount']:,.2f}"
            ]
            item = self.tree.insert('', 'end', values=vals)
            if i in self.highlight:
                self.tree.tag_configure('hl', background='lightyellow')
                self.tree.item(item, tags=('hl',))

    def apply_filter(self):
        sel = self.client_cb.get()
        if not sel:
            messagebox.showwarning("Ошибка", "Выберите клиента!")
            return
        try:
            self.client_id = int(sel.split("ID:")[1].split(')')[0])
            self.load_orders()
            self.status(f"Фильтр: {sel.split(' (ID:')[0]}")
        except:
            messagebox.showerror("Ошибка", "Не применить фильтр!")

    def clear_filter(self):
        self.client_id = None
        self.client_cb.set('')
        self.load_orders()
        self.status("Фильтр отключен")

    def search(self):
        text = self.search_entry.get().strip()
        if not text:
            self.highlight = []
            self.display()
            return

        self.highlight = []
        for i, r in enumerate(self.data):
            if (text.lower() in str(r['id_order']).lower() or
                    (r['client_name'] and text.lower() in r['client_name'].lower()) or
                    (r['client_phone'] and text.lower() in r['client_phone'].lower())):
                self.highlight.append(i)

        self.display()
        cnt = len(self.highlight)
        messagebox.showinfo("Результат", f"Найдено: {cnt}" if cnt else "Ничего не найдено!")
        self.status(f"Найдено: {cnt}" if cnt else "Ничего не найдено")

    def update_stats(self):
        sql = "SELECT COUNT(*) as cnt, COALESCE(SUM(total_amount),0) as sm FROM orders_june_2025"
        params = []
        if self.client_id:
            sql += " WHERE id_customer = %s"
            params.append(self.client_id)

        self.cur.execute(sql, params)
        r = self.cur.fetchone()
        self.lbl_count.config(text=f"Заказов: {r['cnt']}")
        self.lbl_sum.config(text=f"Сумма: {float(r['sm']):,.2f} руб.")

    def status(self, msg):
        self.lbl_status.config(text=msg)
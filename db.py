import mariadb

class DB:
    def __init__(self):
        self.cur = None
        self.conn = None

    def connect(self):
        try:
            self.conn = mariadb.connect(host='192.168.0.176', user='aa', password='12345678', database='milk')
            self.cur = self.conn.cursor(dictionary=True)
            return True
        except:
            return False

    def get_clients(self):
        self.cur.execute("SELECT id_customer, name FROM customers WHERE buyer=1 ORDER BY name")
        return self.cur.fetchall()

    def get_orders(self, client_id=None, sort='date_order', order='DESC'):
        sql = "SELECT o.id_order, o.date_order, o.total_amount, c.name as client_name, c.phone as client_phone FROM orders_june_2025 o LEFT JOIN customers c ON o.id_customer = c.id_customer"
        p = []
        if client_id:
            sql += " WHERE o.id_customer = %s"
            p.append(client_id)
        sort = 'c.name' if sort == 'client_name' else f'o.{sort}'
        self.cur.execute(f"{sql} ORDER BY {sort} {order}", p)
        for r in self.cur.fetchall():
            r['total_amount'] = r['total_amount'] or 0
            yield r

    def get_summary(self, client_id=None):
        sql = "SELECT COUNT(*) as c, COALESCE(SUM(total_amount),0) as s FROM orders_june_2025"
        p = []
        if client_id:
            sql += " WHERE id_customer = %s"
            p.append(client_id)
        self.cur.execute(sql, p)
        r = self.cur.fetchone()
        return r['c'], float(r['s'])

    def get_details(self, oid):
        self.cur.execute(
            "SELECT p.name_product, os.quantity, p.unit, os.amount FROM orders_structure os LEFT JOIN products p ON os.id_product = p.id_product WHERE os.id_order = %s",
            (oid,))
        return self.cur.fetchall()


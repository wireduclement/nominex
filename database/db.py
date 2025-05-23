import pymysql

class Database:
    def __init__(self, host, user, password, database):
        self.host, self.user, self.password, self.database = host, user, password, database
        
        # create connection
        try:
            self.my_db = pymysql.connect(
                host=self.host, 
                user=self.user, 
                password=self.password, 
                database=self.database
            )
        
            self.cursor = self.my_db.cursor()
            self.sql = ""

        except Exception as err:
            print(err)

    def insert(self, table, columns, values):
        self.sql = f"INSERT INTO {table} ("
        if isinstance(columns, list):
            for col in columns:
                self.sql += f"`{col}`, "
            self.sql = self.sql.rstrip(", ")
            self.sql += ") VALUES ("
        else:
            raise TypeError(f"Expected a list but found {type(columns)}")
        
        if isinstance(values, list):
            for val in values:
                self.sql += f"'{val}', "
            self.sql = self.sql.rstrip(", ")
            self.sql += ")"
        else:
            raise TypeError(f"Expected a list but found {type(values)}")
        
        
        self.cursor.execute(self.sql)
        self.my_db.commit()


    def read(self, table, clause=None, columns=None, like=False):
        if not columns:
            self.sql = f"SELECT * FROM {table}"
        else:
            if isinstance(columns, list):
                self.sql = f"SELECT {', '.join(columns)} FROM {table}"
            else:
                raise TypeError(f"Expected a list but found {type(columns)}")

        values = []
        
        if clause and isinstance(clause, dict):
            self.sql += " WHERE "
            conditions = []
            for key, val in clause.items():
                if like:  # Enable LIKE queries
                    conditions.append(f"{key} LIKE %s")
                    values.append(f"%{val}%")  # Add wildcard for partial matches
                else:
                    conditions.append(f"{key} = %s")
                    values.append(val)  

            self.sql += " AND ".join(conditions)

        self.cursor.execute(self.sql, tuple(values))
        results = self.cursor.fetchall()
        return results


    def delete(self, table_name, clause):
        self.sql = f"DELETE FROM {table_name} WHERE "
        conditions = []
        for key, value in clause.items():
            conditions.append(f"{key}=%s")
        self.sql += " AND ".join(conditions)
        self.cursor.execute(self.sql, tuple(clause.values()))
        self.my_db.commit()


    def update(self, table, update, clause):
        set_clause = ", ".join([f"{key}=%s" for key in update.keys()])
        where_clause = " AND ".join([f"{key}=%s" for key in clause.keys()])
        self.sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        values = list(update.values()) + list(clause.values())
        self.cursor.execute(self.sql, values)
        self.my_db.commit()


    def count_rows(self, table):
        self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
        result = self.cursor.fetchone()
        return result[0]

     
    def close(self):
        self.my_db.close()

                
if __name__ == "__main__":
    db = Database("localhost", "root", "", "voting_db")
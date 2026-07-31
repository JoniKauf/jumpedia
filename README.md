# Jumpedia

This is the source code of **Jumpedia**.

> **Note:** The project is currently **private**.

This README grows whenever we think of something worth documenting, so expect it to be a living document rather than a complete reference.

---

# How To Run

1. Install the uv package manager.
2. Open the Jumpedia folder in VSCode or your preferred IDE (I use VSCode so no guarantees).
3. Use the command `uv sync` to install all dependencies.
4. At the root directory create the `.env` file with the same layout as in `.env.example` and fill out the fields.
5. Create a localhost mariadb database (for example with MySQL workbench) called `jumpedia`.
6. Execute this script to create the user `jumpedia@%`, use the password you specified in the `.env` file:
```SQL
CREATE USER 'jumpedia'@'%' IDENTIFIED BY 'INSERT YOUR PASSWORD HERE';

GRANT CREATE, ALTER, INDEX, SELECT, INSERT, UPDATE, DELETE
ON jumpedia.*
TO 'jumpedia'@'%';
```
7. If I forgot something, extend this! :)
8. Run with the command `uv run jumpedia`.

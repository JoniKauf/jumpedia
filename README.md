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
8. Run with the command `uv run python -m src` and create the DB when prompted.

---

# Domain-Specific Knowledge

Like every codebase, Jumpedia has knowledge that is specific to its own architecture and terminology. We try to keep this "domain knowledge" to a minimum because every extra concept makes onboarding new contributors harder.

This section documents the concepts that are unique to Jumpedia and may not be immediately obvious.

---

# Architecture

## A bit of history

Before this 3rd (or maybe 4th...) rewrite of Jumpedia, I (Joni) didn't really know much about established software architecture. I simply organized the project in whatever way felt reasonable at the time.

It worked... for a while.

Eventually the codebase became increasingly difficult to extend, responsibilities blurred together, and making changes became frustrating.

This rewrite adopts a lightweight version of **Domain-Driven Design (DDD)**. It isn't a textbook implementation, but it follows the same general ideas and has proven much easier to reason about.

---

## Layer overview

The project is split into four primary layers.

```text
Interfaces  
     │       \
Services --- Domain
     │       /
Repositories 
```

Each layer may only depend on the layers below it.

---

## Domain

`domain/`

The domain layer is the foundation of the project.

It contains the core concepts of Jumpedia, including entities, value objects, enums, exceptions, and other business primitives.

Everything else in the project depends on this layer, which means the domain itself **must never depend on anything outside `domain/`**.

---

## Repositories

`repositories/`

Repositories are responsible for talking to the database.

They know only about the domain layer and intentionally contain **no business logic**.

Their responsibilities include:

- Loading data
- Storing data
- Updating data
- Deleting data

They are deliberately "dumb." They simply translate between the database and domain objects.

---

## Services

`services/`

Services contain **all business logic**.

They know about both the domain layer and repositories, using repositories whenever database access is required.

There are two categories of services:

- **Public services** — the API exposed to interfaces.
- **Internal services** — reusable building blocks used by other services to avoid duplicated logic.

Whenever a rule, validation, permission check, or workflow exists, it belongs here.

---

## Interfaces

`interfaces/`

Interfaces are responsible for interacting with the outside world.

They know about the domain layer and services, but **never communicate directly with repositories**.

Their responsibilities include:

- Handling Discord commands
- Parsing user input (using the DSLs)
- Calling services
- Formatting service results for presentation
- Displaying responses back to users

In short, interfaces are responsible for **how** users interact with Jumpedia, while services are responsible for **what** Jumpedia does.
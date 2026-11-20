-- =========================================================
-- PRACTICA1CHAT - BASE DE DATOS BDD_Messenger
-- SQL Server 2025 / SQL Server Express
-- Script para reconstruir el esquema sin datos de usuarios.
-- Puede ejecutarse de nuevo sin borrar cuentas existentes.
-- =========================================================

-- 1. CREAR LA BASE DE DATOS SI NO EXISTE
IF DB_ID(N'BDD_Messenger') IS NULL
BEGIN
    CREATE DATABASE [BDD_Messenger];
END;
GO

USE [BDD_Messenger];
GO

-- 2. CREAR LA TABLA ORIGINAL SI NO EXISTE
IF OBJECT_ID(N'dbo.Usuarios', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Usuarios (
        id_usuario INT IDENTITY(1,1) PRIMARY KEY,
        nombre_usuario NVARCHAR(50) NOT NULL UNIQUE,
        fecha_registro DATETIME2 DEFAULT SYSDATETIME()
    );
END;
GO

-- 3. AGREGAR LAS COLUMNAS DE LAS CUENTAS SI FALTAN
IF COL_LENGTH('dbo.Usuarios', 'id_publico') IS NULL
BEGIN
    ALTER TABLE dbo.Usuarios
    ADD id_publico UNIQUEIDENTIFIER NOT NULL
        CONSTRAINT DF_Usuarios_IdPublico DEFAULT NEWID();
END;
GO

IF COL_LENGTH('dbo.Usuarios', 'nombre_mostrar') IS NULL
BEGIN
    ALTER TABLE dbo.Usuarios
    ADD nombre_mostrar NVARCHAR(50) NULL;
END;
GO

IF COL_LENGTH('dbo.Usuarios', 'contrasena_hash') IS NULL
BEGIN
    ALTER TABLE dbo.Usuarios
    ADD contrasena_hash NVARCHAR(255) NULL;
END;
GO

IF COL_LENGTH('dbo.Usuarios', 'ultima_ip') IS NULL
BEGIN
    ALTER TABLE dbo.Usuarios
    ADD ultima_ip VARCHAR(45) NULL;
END;
GO

-- 4. CONSERVAR COMO NOMBRE VISIBLE EL USUARIO PREEXISTENTE
UPDATE dbo.Usuarios
SET nombre_mostrar = nombre_usuario
WHERE nombre_mostrar IS NULL;
GO

-- 5. GARANTIZAR QUE EL GUID DE CADA CUENTA SEA ÚNICO
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'UX_Usuarios_IdPublico'
      AND object_id = OBJECT_ID(N'dbo.Usuarios')
)
BEGIN
    CREATE UNIQUE INDEX UX_Usuarios_IdPublico
    ON dbo.Usuarios(id_publico);
END;
GO

-- 6. COMPROBAR LA ESTRUCTURA (SIN MOSTRAR HASHES)
SELECT
    id_usuario,
    id_publico,
    nombre_usuario,
    nombre_mostrar,
    ultima_ip,
    fecha_registro
FROM dbo.Usuarios
ORDER BY id_usuario;
GO

-- NOTAS:
-- * La contraseña original NO se almacena: db.py genera hashes Argon2id.
-- * nombre_usuario es único; nombre_mostrar puede repetirse.
-- * La IP NO identifica de manera permanente al usuario; se usa id_publico.
-- * Este script NO contiene contraseñas, hashes ni registros personales.
-- * Los usuarios nuevos se crean desde Registro en la aplicación.

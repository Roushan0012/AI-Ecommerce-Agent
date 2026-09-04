-- Add image_url column to products table
-- Migration: 003_add_product_image_url.sql
-- Description: Adds nullable image_url TEXT column to products table

ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url TEXT;

# **Project Plan: "Fulcrum" \- The AI-Powered Commerce Hub**

**Document Version:** 3.0 (Standalone Production Blueprint) **Last Updated:** October 6, 2025

## **1\. Executive Summary**

Fulcrum is a comprehensive, AI-first platform designed to streamline the entire product lifecycle. It provides a single, central point of control (a "fulcrum") for inventory management, supplier orders, multi-channel sales, and business analytics.  
Key differentiators include a **Progressive Web App (PWA) architecture for the management interface, ensuring a seamless, native-like experience on web, Android, and iOS from a single codebase**. It features a modular, AI-agnostic architecture, a powerful generative AI suite, a state-of-the-art semantic search engine, and deep, bi-directional integration with third-party marketplaces. This plan details an eight-phase roadmap, ensuring a scalable and future-proof solution.  
**Project Name:** Fulcrum

## **2\. Table of Contents**

1. Executive Summary  
2. Core Architectural Principles & Configuration  
3. System Architecture & Tech Stack  
4. Finalized Database Schema  
5. Phased Development Plan  
   * Phase 1: The Core Foundation & Search Backend  
   * Phase 2: The Cross-Platform PWA Management App  
   * Phase 3: Intelligent Product Ingestion & Indexing  
   * Phase 4: AI Content Generation & Media Management  
   * Phase 5: AI-Powered Purchase Order Management  
   * Phase 6: Deep Marketplace Integration Engine  
   * Phase 7: The Hybrid E-commerce Storefront  
   * Phase 8: Advanced Multi-Channel Analytics  
6. Future Roadmap

## **3\. Core Architectural Principles & Configuration**

* **PWA for Management Interface:** The Angular management app will be built as a Progressive Web App. This includes a service worker for offline capabilities and a web app manifest, allowing users to "Install" it to their home screen on any device for a full-screen, native feel.  
* **Hardware Abstraction:** The PWA will access device hardware (camera, Bluetooth) through modern browser APIs (getUserMedia, Web Bluetooth API), ensuring broad compatibility without native code.  
* **Decoupled & Simple Deployment:**  
  * **Backend:** A single Docker Compose file will manage the entire backend stack (API, database, workers), enabling one-command deployment.  
  * **Customer Frontend:** The Angular e-commerce app will be built into static HTML/CSS/JS files, which can be deployed easily and cheaply on any static hosting provider (e.g., Netlify, Vercel, AWS S3 with CloudFront).  
* **Configuration Management:** The backend will be configured via environment variables, loaded by Pantic's BaseSettings from a .env file for local development.  
* **Graceful Degradation:** AI features are enhancements. If disabled, the application remains fully functional for all manual operations.

## **4\. System Architecture & Tech Stack**

* **Frontend (Management PWA & E-commerce):** Angular, Angular Material, ngx-scanner, ngx-charts, Angular PWA module (@angular/pwa).  
* **Backend:** Python, FastAPI, SQLAlchemy, Alembic, Pydantic, Celery & Redis.  
* **Database:** PostgreSQL with the pgvector extension.  
* **Deployment:** Docker & Docker Compose for the backend, Static Host/Nginx for the e-commerce frontend.

## **5\. Finalized Database Schema**

* users: id, email, hashed\_password, role  
* app\_settings: id, ai\_provider, ai\_api\_key\_encrypted, file\_storage\_provider, theme\_settings  
* suppliers: id, name, contact\_person, email, phone  
* products: id, name, description, sku, supplier\_id, default\_resale\_price, cost\_price, properties, embedding  
* product\_images: id, product\_id, image\_path, is\_primary, source  
* inventory\_items: id, product\_id, quantity, location  
* **marketplaces (New):** id (PK, Integer), name (String, e.g., 'Mercado Libre'), api\_base\_url (String)  
* **marketplace\_credentials (New):** id (PK), user\_id (FK), marketplace\_id (FK), access\_token (Encrypted), refresh\_token (Encrypted), expires\_at (Timestamp)  
* **marketplace\_listings (New):** id (PK), product\_id (FK), marketplace\_id (FK), external\_listing\_id (String), listing\_url (String), status (String)  
* purchase\_orders & purchase\_order\_items: Unchanged.  
* **sales\_orders (Modified):** id, client\_id, status, total\_price, created\_at, **source (Enum\['FULCRUM', 'MERCADOLIBRE', 'AMAZON'\])**, **external\_order\_id (String)**  
* sales\_order\_items: Unchanged.

## **6\. Phased Development Plan**

### **Phase 1: The Core Foundation & Search Backend**

**Goal:** Establish a configurable, secure backend API with all necessary abstractions and a functional search engine.  
**Backend Tasks:**

1. **Project Setup:** Initialize FastAPI, Docker, Celery, Redis, and PostgreSQL with pgvector.  
2. **Configuration:** Implement Pydantic BaseSettings for environment-variable-driven configuration.  
3. **Abstraction Layers:** Create base classes for AIService and FileStorageService.  
4. **Models & APIs:** Implement SQLAlchemy models (including new marketplace tables) and standard CRUD APIs for User, Product, Supplier, Marketplace.  
5. **Search & Indexing Logic:** Implement the GET /search/products endpoint using pgvector and the generate\_product\_embedding Celery task.

### **Phase 2: The Cross-Platform PWA Management App**

**Goal:** A functional, customizable UI for inventory management that works seamlessly on any device.  
**Frontend Tasks:**

1. **PWA Initialization:** Run ng add @angular/pwa. This command will automatically configure the manifest.webmanifest file (for app icon, name, theme color) and set up the service worker for caching and offline capabilities.  
2. **Hardware Integration Service:** Create a HardwareService in Angular that wraps browser APIs.  
   * getCameraStream(): Uses navigator.mediaDevices.getUserMedia to access the camera.  
   * This service will be used by scanner components.  
3. **Core UI Components:** Build standard CRUD interfaces (ProductListComponent, ProductDetailComponent, etc.).  
4. **AI Search Bar:** Implement the AiSearchBarComponent with voice input and integrate it into the ProductListComponent.  
5. **Settings Page:** Build the SettingsComponent for administrators to configure the application.

### **Phase 3: Intelligent Product Ingestion & Indexing**

**Goal:** Automate product creation via camera or scanner, leveraging the PWA's hardware access.  
**Backend Tasks:**

1. **Indexing on Save:** Ensure the generate\_product\_embedding background task is dispatched whenever a product is created or updated.  
2. **Upload & Analysis Endpoints:** Implement /uploads/generate-url and /ai/identify-from-image.

**Frontend Tasks:**

1. **Scanner Integration:** The ProductIngestionComponent will use the HardwareService to get the camera feed and pass it to a library like ngx-scanner to continuously scan for barcodes and QR codes.  
2. **Photo Ingestion:** The "Take Photo" button will also use the HardwareService to capture an image before sending it through the upload and analysis flow.

### **Phase 4: AI Content Generation & Media Management**

**Goal:** Empower users to create professional marketing assets directly within the product management interface. *(Tasks remain the same, focusing on the MediaManagerComponent and backend generation endpoints.)*

### **Phase 5: AI-Powered Purchase Order Management**

**Goal:** Streamline inbound inventory from supplier documents and provide a robust receiving workflow. *(Tasks remain the same, focusing on the AI parsing endpoint and transactional receiving logic.)*

### **Phase 6: Deep Marketplace Integration Engine**

**Goal:** Create a scalable system to list products, synchronize stock, and pull in sales from third-party platforms.  
**Backend Tasks:**

1. **Abstraction Layer:** Create a MarketplaceConnector abstract class with methods publish\_product, update\_stock, handle\_oauth\_callback, and handle\_webhook.  
2. **Concrete Implementation:** Implement MercadoLibreConnector and a placeholder AmazonConnector.  
3. **AI-Assisted Listing:**  
   * Create a new endpoint: POST /ai/products/{product\_id}/generate-listing-description. This endpoint accepts a marketplace\_name and generates a description tailored to that platform's audience and style.  
4. **Order Synchronization:**  
   * Create webhook endpoints: POST /webhooks/mercadolibre, POST /webhooks/amazon.  
   * When a webhook is hit with a new order payload, the handle\_webhook method of the correct connector will be called. It will parse the data, create a SalesOrder with the correct source and external\_order\_id, and decrement stock.  
   * The stock decrement action will trigger the sync\_stock\_for\_product Celery task, which updates the stock levels on **all other** configured marketplaces to prevent overselling.  
5. **API Endpoints:** Implement endpoints for the entire listing and authentication lifecycle.

**Frontend Tasks:**

1. **Marketplace UI:** The "Listings" tab in ProductDetailComponent will now manage the full lifecycle.  
2. **AI-Powered Listing Flow:** The modal for listing a product will now have a text area for the description, pre-filled with the product's default description, and a button "Generate with AI for \[Marketplace Name\]" which calls the new generation endpoint.  
3. **Settings Integration:** Add a new section to the SettingsComponent for managing marketplace connections, initiating the OAuth flow for each platform.

### **Phase 7: The Hybrid E-commerce Storefront**

**Goal:** A public-facing shop where customers can either buy directly or seamlessly navigate to third-party marketplace listings.  
**Backend Tasks:**

1. **Public API Expansion:** The GET /public/products/{product\_id} endpoint must now join with the marketplace\_listings table to return a list of external purchasing options.  
2. **Checkout & Order Logic:** Implement Stripe integration and webhook handlers for on-site purchases, ensuring SalesOrder records are created with the source set to 'FULCRUM'.

**Frontend Tasks (E-commerce App):**

1. **Static Deployment:** Configure the Angular build process (angular.json) for production, which will generate static files. Document the simple process of deploying these files to a static host.  
2. **Hybrid Purchase Component:** In the PublicProductDetailComponent, create a new "Purchase Options" component.  
   * It will always show the primary "Add to Cart" button for on-site checkout.  
   * Below this, it will render a "Also available at:" section. It will dynamically display buttons with logos (e.g., Mercado Libre, Amazon) for each entry returned from the API, linking to the listing\_url.

### **Phase 8: Advanced Multi-Channel Analytics**

**Goal:** Provide business insights that differentiate between sales channels.  
**Backend Tasks:**

1. **Reporting Endpoint Enhancement:** Modify all reporting endpoints (e.g., /reports/sales-summary) to accept an optional channel query parameter (e.g., ?channel=MERCADOLIBRE) to filter the data.

**Frontend Tasks:**

1. **Dashboard Filtering:** Add a dropdown/button group to the DashboardAnalyticsComponent allowing the user to filter all charts and stats by sales channel ("All Channels", "Fulcrum", "Mercado Libre", etc.). This provides an immediate, clear view of performance across all integrated platforms.

## **7\. Future Roadmap**

* **Multi-Modal Search:** Allow image-based search queries ("find products that look like this").  
* **AI Video Generation:** Integrate emerging video generation APIs.  
* **Advanced Integrations:** Accounting (QuickBooks, Xero) and Shipping (Shippo, EasyPost).  
* **Supplier Portal:** A secure login for suppliers to view and update their POs.


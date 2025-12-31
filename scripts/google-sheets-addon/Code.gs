/**
 * Fulcrum Connect - Google Sheets Add-on
 * 
 * This Apps Script provides bidirectional sync between Google Sheets
 * and your Fulcrum inventory management system.
 * 
 * SETUP INSTRUCTIONS:
 * 1. Open your Google Sheet
 * 2. Go to Extensions > Apps Script
 * 3. Delete any existing code and paste this entire file
 * 4. Update FULCRUM_API_URL and FULCRUM_API_KEY below
 * 5. Save and refresh your Sheet
 * 6. Use the "Fulcrum" menu that appears
 */

// =============================================================================
// CONFIGURATION
// =============================================================================

/**
 * Get configuration from Script Properties (secure storage).
 * Users set these via the setup dialog.
 */
function getConfig() {
  const props = PropertiesService.getScriptProperties();
  return {
    FULCRUM_API_URL: props.getProperty('FULCRUM_API_URL') || 'http://localhost:8000/api/v1',
    FULCRUM_API_KEY: props.getProperty('FULCRUM_API_KEY') || '',
    SHEETS: {
      PRODUCTS: 'Products',
      INVENTORY: 'Inventory',
      SUPPLIERS: 'Suppliers'
    }
  };
}

// =============================================================================
// MENU & UI
// =============================================================================

/**
 * Creates the custom menu when the spreadsheet opens.
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('⚙️ Fulcrum')
    .addItem('🔧 Setup Connection', 'showSetupDialog')
    .addSeparator()
    .addItem('🔄 Pull Products', 'pullProducts')
    .addItem('📦 Pull Inventory', 'pullInventory')
    .addItem('🏭 Pull Suppliers', 'pullSuppliers')
    .addSeparator()
    .addItem('⬆️ Push Changes to Fulcrum', 'pushChanges')
    .addSeparator()
    .addItem('📋 View Sync Log', 'showSyncLog')
    .addToUi();
}

/**
 * Shows the setup dialog for API connection.
 */
function showSetupDialog() {
  const html = HtmlService.createHtmlOutput(`
    <style>
      body { font-family: Arial, sans-serif; padding: 20px; }
      h3 { margin-top: 0; color: #2E3A59; }
      label { display: block; margin-top: 15px; font-weight: bold; }
      input { width: 100%; padding: 8px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px; }
      button { margin-top: 20px; padding: 10px 20px; background: #00BFA5; color: white; border: none; border-radius: 4px; cursor: pointer; }
      button:hover { background: #008E7B; }
      .help { font-size: 12px; color: #666; margin-top: 5px; }
    </style>
    <h3>🔧 Fulcrum Connection Setup</h3>
    <p>Enter your Fulcrum API details below. You can generate an API key from <strong>Settings > Integrations</strong> in Fulcrum.</p>
    
    <label>API URL</label>
    <input type="text" id="apiUrl" placeholder="http://localhost:8000/api/v1">
    <div class="help">Your Fulcrum backend URL (no trailing slash)</div>
    
    <label>API Key</label>
    <input type="password" id="apiKey" placeholder="Paste your API key here">
    <div class="help">Generate this from Fulcrum Settings > Integrations > API Keys</div>
    
    <button onclick="saveConfig()">Save & Connect</button>
    
    <script>
      // Load existing values
      google.script.run.withSuccessHandler(function(config) {
        document.getElementById('apiUrl').value = config.url || '';
        document.getElementById('apiKey').value = config.key ? '********' : '';
      }).getExistingConfig();
      
      function saveConfig() {
        const url = document.getElementById('apiUrl').value;
        const key = document.getElementById('apiKey').value;
        if (!key || key === '********') {
          alert('Please enter your API key');
          return;
        }
        google.script.run.withSuccessHandler(function() {
          alert('Connection saved! You can now use the Fulcrum menu.');
          google.script.host.close();
        }).saveApiConfig(url, key);
      }
    </script>
  `)
    .setWidth(450)
    .setHeight(350);
  
  SpreadsheetApp.getUi().showModalDialog(html, 'Fulcrum Setup');
}

/**
 * Get existing config for the setup dialog.
 */
function getExistingConfig() {
  const props = PropertiesService.getScriptProperties();
  return {
    url: props.getProperty('FULCRUM_API_URL') || '',
    key: props.getProperty('FULCRUM_API_KEY') ? true : false
  };
}

/**
 * Save API configuration securely.
 */
function saveApiConfig(url, key) {
  const props = PropertiesService.getScriptProperties();
  props.setProperty('FULCRUM_API_URL', url);
  props.setProperty('FULCRUM_API_KEY', key);
}

/**
 * Shows a toast notification.
 */
function showToast(message, title = 'Fulcrum') {
  SpreadsheetApp.getActiveSpreadsheet().toast(message, title, 5);
}

// =============================================================================
// PULL OPERATIONS (Fulcrum -> Sheets)
// =============================================================================

/**
 * Pull products from Fulcrum and populate the Products sheet.
 */
function pullProducts() {
  try {
    showToast('Fetching products from Fulcrum...', '🔄 Syncing');
    
    const response = fetchFromFulcrum('/integrations/sheets/sync-pull', 'POST', {
      entity: 'products'
    });
    
    if (!response.data || response.data.length === 0) {
      showToast('No products found in Fulcrum', '⚠️ Warning');
      return;
    }
    
    const config = getConfig();
    const sheet = getOrCreateSheet(config.SHEETS.PRODUCTS);
    sheet.clear();
    
    // Headers
    const headers = ['ID', 'SKU', 'Name', 'Cost Price', 'Resale Price', 'Stock'];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
    
    // Data rows
    const rows = response.data.map(p => [
      p.id, p.sku, p.name, p.cost_price, p.resale_price, p.stock
    ]);
    
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
    }
    
    // Format
    sheet.autoResizeColumns(1, headers.length);
    
    showToast(`Pulled ${response.total_records} products successfully!`, '✅ Done');
    
  } catch (error) {
    showToast(`Error: ${error.message}`, '❌ Error');
    Logger.log('Pull Products Error: ' + error);
  }
}

/**
 * Pull inventory levels from Fulcrum.
 */
function pullInventory() {
  try {
    showToast('Fetching inventory from Fulcrum...', '🔄 Syncing');
    
    const response = fetchFromFulcrum('/integrations/sheets/sync-pull', 'POST', {
      entity: 'inventory'
    });
    
    const config = getConfig();
    const sheet = getOrCreateSheet(config.SHEETS.INVENTORY);
    sheet.clear();
    
    const headers = ['Product ID', 'SKU', 'Name', 'Stock Quantity'];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
    
    const rows = response.data.map(p => [p.product_id, p.sku, p.name, p.stock]);
    
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
    }
    
    sheet.autoResizeColumns(1, headers.length);
    showToast(`Pulled inventory for ${response.total_records} products!`, '✅ Done');
    
  } catch (error) {
    showToast(`Error: ${error.message}`, '❌ Error');
    Logger.log('Pull Inventory Error: ' + error);
  }
}

/**
 * Pull suppliers from Fulcrum.
 */
function pullSuppliers() {
  try {
    showToast('Fetching suppliers from Fulcrum...', '🔄 Syncing');
    
    const response = fetchFromFulcrum('/integrations/sheets/sync-pull', 'POST', {
      entity: 'suppliers'
    });
    
    const config = getConfig();
    const sheet = getOrCreateSheet(config.SHEETS.SUPPLIERS);
    sheet.clear();
    
    const headers = ['ID', 'Name', 'Email', 'Phone'];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
    
    const rows = response.data.map(s => [s.id, s.name, s.email, s.phone]);
    
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
    }
    
    sheet.autoResizeColumns(1, headers.length);
    showToast(`Pulled ${response.total_records} suppliers!`, '✅ Done');
    
  } catch (error) {
    showToast(`Error: ${error.message}`, '❌ Error');
    Logger.log('Pull Suppliers Error: ' + error);
  }
}

// =============================================================================
// PUSH OPERATIONS (Sheets -> Fulcrum)
// =============================================================================

/**
 * Push local changes back to Fulcrum.
 * Currently tracks changes to the Products sheet.
 */
function pushChanges() {
  try {
    showToast('Preparing to push changes...', '⬆️ Pushing');
    
    const config = getConfig();
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(config.SHEETS.PRODUCTS);
    if (!sheet) {
      showToast('Products sheet not found. Pull products first.', '⚠️ Warning');
      return;
    }
    
    // Get data (skip header row)
    const data = sheet.getDataRange().getValues();
    if (data.length <= 1) {
      showToast('No data to push', 'ℹ️ Info');
      return;
    }
    
    const headers = data[0];
    const changes = [];
    
    // For now, we'll push all rows as potential changes
    // A more sophisticated approach would track actual edits
    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const id = row[0];
      const costPrice = row[3];
      const resalePrice = row[4];
      
      // Push cost price change
      if (costPrice !== '') {
        changes.push({
          id: id,
          field: 'cost_price',
          new_value: costPrice
        });
      }
      
      // Push resale price change  
      if (resalePrice !== '') {
        changes.push({
          id: id,
          field: 'resale_price',
          new_value: resalePrice
        });
      }
    }
    
    if (changes.length === 0) {
      showToast('No changes detected to push', 'ℹ️ Info');
      return;
    }
    
    const response = fetchFromFulcrum('/integrations/sheets/sync-push', 'POST', {
      entity: 'products',
      changes: changes
    });
    
    if (response.success) {
      showToast(`Updated ${response.updated_count} records in Fulcrum!`, '✅ Done');
    } else {
      showToast(`Partial success: ${response.updated_count} updated, ${response.errors.length} errors`, '⚠️ Warning');
      Logger.log('Push Errors: ' + JSON.stringify(response.errors));
    }
    
  } catch (error) {
    showToast(`Error: ${error.message}`, '❌ Error');
    Logger.log('Push Changes Error: ' + error);
  }
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Make an authenticated request to the Fulcrum API.
 */
function fetchFromFulcrum(endpoint, method = 'GET', payload = null) {
  const config = getConfig();
  
  if (!config.FULCRUM_API_KEY) {
    throw new Error('API key not configured. Use "Setup Connection" from the Fulcrum menu.');
  }
  
  const url = config.FULCRUM_API_URL + endpoint;
  
  const options = {
    method: method,
    headers: {
      'X-API-Key': config.FULCRUM_API_KEY,
      'Content-Type': 'application/json'
    },
    muteHttpExceptions: true
  };
  
  if (payload) {
    options.payload = JSON.stringify(payload);
  }
  
  const response = UrlFetchApp.fetch(url, options);
  const code = response.getResponseCode();
  
  if (code >= 400) {
    throw new Error(`API Error ${code}: ${response.getContentText()}`);
  }
  
  return JSON.parse(response.getContentText());
}

/**
 * Get or create a sheet with the given name.
 */
function getOrCreateSheet(name) {
  const config = getConfig();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(config.SHEETS[name] || name);
  
  if (!sheet) {
    sheet = ss.insertSheet(config.SHEETS[name] || name);
  }
  
  return sheet;
}

/**
 * Show configuration dialog for API settings.
 */
function showConfigDialog() {
  const html = HtmlService.createHtmlOutput(`
    <h3>Fulcrum Configuration</h3>
    <p>To configure your API connection:</p>
    <ol>
      <li>Open the Apps Script editor (Extensions > Apps Script)</li>
      <li>Update the CONFIG object at the top of Code.gs</li>
      <li>Set your FULCRUM_API_URL and FULCRUM_API_KEY</li>
      <li>Save and refresh</li>
    </ol>
    <p><strong>Current API URL:</strong> ${CONFIG.FULCRUM_API_URL}</p>
  `)
    .setWidth(400)
    .setHeight(250);
  
  SpreadsheetApp.getUi().showModalDialog(html, 'Fulcrum Settings');
}

/**
 * Show sync log.
 */
function showSyncLog() {
  const logs = Logger.getLog();
  const html = HtmlService.createHtmlOutput(`
    <h3>Sync Log</h3>
    <pre style="font-size: 11px; max-height: 300px; overflow: auto;">${logs || 'No logs yet.'}</pre>
  `)
    .setWidth(500)
    .setHeight(350);
  
  SpreadsheetApp.getUi().showModalDialog(html, 'Sync Log');
}

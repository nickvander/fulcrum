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
 * 4. Save and refresh your Sheet
 * 5. Use "⚙️ Fulcrum > 🔧 Setup Connection" to connect
 */

// =============================================================================
// CONFIGURATION
// =============================================================================

function getConfig() {
  const props = PropertiesService.getScriptProperties();
  return {
    FULCRUM_API_URL: props.getProperty('FULCRUM_API_URL') || 'http://localhost:8000/api/v1',
    FULCRUM_API_KEY: props.getProperty('FULCRUM_API_KEY') || '',
    SHEETS: {
      PRODUCTS: 'Products',
      INVENTORY: 'Inventory',
      SUPPLIERS: 'Suppliers',
      POS: 'Purchase Orders',
      EXPENSES: 'Expenses'
    },
    COLORS: {
      PRIMARY: '#1a73e8', // Fulcrum Blue
      HEADER_TEXT: '#ffffff',
      BANDING_1: '#ffffff',
      BANDING_2: '#f8f9fa'
    }
  };
}

// =============================================================================
// LOGGING SYSTEM
// =============================================================================

/**
 * Appends a message to the persistent log.
 */
function logInfo(message) {
  const timestamp = new Date().toLocaleTimeString();
  const entry = `[${timestamp}] ${message}`;
  Logger.log(entry); // Keep native logging too
  
  try {
    const props = PropertiesService.getScriptProperties();
    let logs = props.getProperty('SYNC_LOGS') || '';
    
    // Append new line
    logs = entry + '\n' + logs;
    
    // Truncate to last ~2000 chars to avoid property limits
    if (logs.length > 2000) {
      logs = logs.substring(0, 2000);
      logs = logs.substring(0, logs.lastIndexOf('\n')); // Clean cut
    }
    
    props.setProperty('SYNC_LOGS', logs);
  } catch (e) {
    console.error('Logging failed', e);
  }
}

function clearLogs() {
  PropertiesService.getScriptProperties().deleteProperty('SYNC_LOGS');
}

function getLogHistory() {
  return PropertiesService.getScriptProperties().getProperty('SYNC_LOGS') || 'No logs yet.';
}

// =============================================================================
// MENU & UI
// =============================================================================

function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('⚙️ Fulcrum')
    .addItem('🔧 Setup Connection', 'showSetupDialog')
    .addSeparator()
    .addItem('🔄 Pull All Data', 'pullAll')
    .addSeparator()
    .addItem('📦 Pull Products', 'pullProducts')
    .addItem('📊 Pull Inventory', 'pullInventory')
    .addItem('🏭 Pull Suppliers', 'pullSuppliers')
    .addItem('📜 Pull Purchase Orders', 'pullPurchaseOrders')
    .addItem('💸 Pull Expenses', 'pullExpenses')
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
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 16px; overflow: hidden; font-size: 13px; color: #3c4043; margin: 0; }
      h3 { margin: 0 0 16px 0; color: #1a73e8; font-size: 16px; display: flex; align-items: center; gap: 8px; }
      label { display: block; margin-top: 12px; font-weight: 500; font-size: 12px; color: #5f6368; }
      input { width: 100%; padding: 8px 10px; margin-top: 4px; border: 1px solid #dadce0; border-radius: 4px; box-sizing: border-box; font-size: 13px; }
      input:focus { border-color: #1a73e8; outline: 2px solid rgba(26,115,232,0.2); }
      .actions { margin-top: 24px; display: flex; justify-content: flex-end; }
      button { padding: 8px 20px; background: #1a73e8; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 500; font-size: 13px; transition: background 0.2s; }
      button:hover { background: #1557b0; box-shadow: 0 1px 2px rgba(60,64,67,0.3); }
      .help { font-size: 11px; color: #80868b; margin-top: 4px; }
    </style>
    <h3>🔧 Fulcrum Connection</h3>
    
    <label>API URL</label>
    <input type="text" id="apiUrl" placeholder="https://.../api/v1">
    <div class="help">e.g. ngrok URL ending in /api/v1</div>
    
    <label>API Key</label>
    <input type="password" id="apiKey" placeholder="Paste your API key here">
    
    <div class="actions">
      <button onclick="saveConfig()">Save & Connect</button>
    </div>
    
    <script>
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
          google.script.host.close();
        }).saveApiConfig(url, key);
      }
    </script>
  `)
    .setWidth(380)
    .setHeight(300);
  
  SpreadsheetApp.getUi().showModalDialog(html, 'Fulcrum Setup');
}

/**
 * Shows a custom styled alert dialog.
 */
function showCustomAlert(title, message, type = 'success') {
  const icon = type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️');
  const color = type === 'success' ? '#1a73e8' : (type === 'error' ? '#d93025' : '#1a73e8');
  
  const html = HtmlService.createHtmlOutput(`
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 24px; text-align: center; color: #3c4043; margin: 0; overflow: hidden; }
      .icon { font-size: 36px; margin-bottom: 16px; }
      h3 { margin: 0 0 12px 0; color: ${color}; font-size: 18px; }
      p { margin: 0 0 24px 0; font-size: 14px; line-height: 1.5; color: #5f6368; white-space: pre-wrap; }
      button { padding: 8px 24px; background: ${color}; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 500; font-size: 13px; }
      button:hover { opacity: 0.9; }
      .secondary { background: #f1f3f4; color: #3c4043; margin-right: 8px; }
    </style>
    <div class="icon">${icon}</div>
    <h3>${title}</h3>
    <p>${message}</p>
    <button onclick="google.script.host.close()">Close</button>
  `)
    .setWidth(400)
    .setHeight(260); 
    
  SpreadsheetApp.getUi().showModalDialog(html, 'Fulcrum');
}

function getExistingConfig() {
  const props = PropertiesService.getScriptProperties();
  return {
    url: props.getProperty('FULCRUM_API_URL') || '',
    key: props.getProperty('FULCRUM_API_KEY') ? true : false
  };
}

function saveApiConfig(url, key) {
  const props = PropertiesService.getScriptProperties();
  props.setProperty('FULCRUM_API_URL', url);
  props.setProperty('FULCRUM_API_KEY', key);
  logInfo('Configuration saved.');
}

// =============================================================================
// PULL OPERATIONS
// =============================================================================

function pullAll() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.toast('Starting full sync...', '🔄 Syncing', 60);
  logInfo('--- Starting Full Sync ---');
  
  try {
    pullProducts(true);
    pullInventory(true);
    pullSuppliers(true);
    pullPurchaseOrders(true);
    pullExpenses(true);
    
    // Cleanup default "Sheet1" if it exists and is empty
    cleanupDefaultSheet();
    
    logInfo('Full Sync completed successfully.');
    showCustomAlert('Sync Complete', 'All data has been successfully pulled from Fulcrum!', 'success');
  } catch (error) {
    logInfo('Full Sync FAILED: ' + error.message);
    showCustomAlert('Sync Failed', error.message, 'error');
  }
}

function pullProducts(silent = false) {
  _genericPull('products', 'Products', 
    ['ID', 'SKU', 'Name', 'Cost Price', 'Resale Price', 'Stock'], 
    p => [p.id, p.sku, p.name, p.cost_price, p.resale_price, p.stock],
    silent);
}

function pullInventory(silent = false) {
  _genericPull('inventory', 'Inventory', 
    ['Product ID', 'SKU', 'Name', 'Stock Quantity'], 
    p => [p.product_id, p.sku, p.name, p.stock],
    silent);
}

function pullSuppliers(silent = false) {
  _genericPull('suppliers', 'Suppliers', 
    ['ID', 'Name', 'Email', 'Phone'], 
    s => [s.id, s.name, s.email, s.phone],
    silent);
}

function pullPurchaseOrders(silent = false) {
  _genericPull('purchase-orders', 'Purchase Orders', 
    ['ID', 'PO #', 'Supplier ID', 'Status', 'Total', 'Date'],
    po => [po.id, po.po_number, po.supplier_id, po.status, po.total_amount, po.date],
    silent);
}

function pullExpenses(silent = false) {
  _genericPull('expenses', 'Expenses', 
    ['ID', 'Description', 'Amount', 'Category', 'Date'],
    e => [e.id, e.description, e.amount, e.category, e.date],
    silent);
}

/**
 * Generic helper for pull operations.
 */
function _genericPull(entity, sheetNameKey, headers, rowMapper, silent = false) {
  try {
    const config = getConfig();
    const sheetName = config.SHEETS[sheetNameKey.toUpperCase()] || sheetNameKey;
    
    if (!silent) {
      SpreadsheetApp.getActiveSpreadsheet().toast(`Fetching ${entity}...`, '🔄 Syncing');
    }
    logInfo(`Pulling ${entity}...`);
    
    const response = fetchFromFulcrum('/integrations/sheets/sync-pull', 'POST', { entity: entity });
    
    const sheet = getOrCreateSheet(sheetName);
    
    if (sheet.getFilter()) {
      sheet.getFilter().remove();
    }
    
    sheet.clear();
    
    // Apply Formatting
    formatSheet(sheet, headers);
    
    const rowCount = response.data ? response.data.length : 0;
    
    if (rowCount > 0) {
      const rows = response.data.map(rowMapper);
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
      
      const range = sheet.getRange(1, 1, rows.length + 1, headers.length);
      range.createFilter();
      
      try {
        range.applyRowBanding(SpreadsheetApp.BandingTheme.LIGHT_GREY);
      } catch (e) { }
    }
    
    sheet.autoResizeColumns(1, headers.length);
    logInfo(`Fetched ${rowCount} ${entity} records.`);
    
  } catch (error) {
    if (!silent) {
      showCustomAlert('Sync Error', `Failed to pull ${entity}:\n${error.message}`, 'error');
    }
    logInfo(`Error pulling ${entity}: ${error.message}`);
    Logger.log(`Pull ${entity} Error: ` + error);
    throw error;
  }
}

/**
 * Format a sheet with standard Fulcrum styling.
 */
function formatSheet(sheet, headers) {
  const config = getConfig();
  
  sheet.setTabColor(config.COLORS.PRIMARY);
  
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setValues([headers]);
  headerRange.setFontWeight('bold');
  headerRange.setBackground(config.COLORS.PRIMARY);
  headerRange.setFontColor(config.COLORS.HEADER_TEXT);
  headerRange.setHorizontalAlignment('center');
  
  sheet.setFrozenRows(1);
}

function cleanupDefaultSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet1 = ss.getSheetByName('Sheet1');
  if (sheet1) {
    if (ss.getSheets().length > 1 && sheet1.getLastRow() === 0 && sheet1.getLastColumn() === 0) {
      ss.deleteSheet(sheet1);
    }
  }
}

// =============================================================================
// PUSH OPERATIONS
// =============================================================================

function pushChanges() {
  try {
    const config = getConfig();
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(config.SHEETS.PRODUCTS);
    
    if (!sheet) {
      showCustomAlert('Warning', 'Products sheet not found. Pull products first.', 'info');
      return;
    }
    
    const data = sheet.getDataRange().getValues();
    if (data.length <= 1) return;
    
    const changes = [];
    
    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const id = row[0];
      if (!id) continue;
      
      const costPrice = row[3];
      const resalePrice = row[4];
      const name = row[2];
      
      if (costPrice !== '') changes.push({ id: id, field: 'cost_price', new_value: costPrice });
      if (resalePrice !== '') changes.push({ id: id, field: 'resale_price', new_value: resalePrice });
      if (name !== '') changes.push({ id: id, field: 'name', new_value: name });
    }
    
    if (changes.length === 0) {
      showCustomAlert('No Changes', 'No data found to push.', 'info');
      return;
    }
    
    const html = HtmlService.createHtmlOutput(`
      <style>
        body { font-family: -apple-system, sans-serif; padding: 15px; text-align: center; margin: 0; overflow: hidden; }
        p { color: #555; }
        .buttons { margin-top: 20px; }
        button { padding: 8px 20px; margin: 0 5px; border-radius: 4px; cursor: pointer; border: none; }
        .confirm { background: #1a73e8; color: white; }
        .cancel { background: #f1f3f4; color: #333; }
      </style>
      <h3>⬆️ Push Changes</h3>
      <p>Changes will be validated. Only edited values will be staged for approval.</p>
      <div class="buttons">
        <button class="cancel" onclick="google.script.host.close()">Cancel</button>
        <button class="confirm" onclick="confirm()">Continue</button>
      </div>
      <script>
        function confirm() {
          google.script.run.withSuccessHandler(function() { google.script.host.close(); }).doPush(${JSON.stringify(changes)});
        }
      </script>
    `).setWidth(380).setHeight(220);
    SpreadsheetApp.getUi().showModalDialog(html, 'Confirm Push');
    
  } catch (error) {
    showCustomAlert('Error', error.message, 'error');
  }
}

function doPush(changes) {
  try {
    SpreadsheetApp.getActiveSpreadsheet().toast('Sending data...', '⬆️ Pushing');
    logInfo(`Pushing ${changes.length} potential changes...`);
    
    const response = fetchFromFulcrum('/integrations/sheets/sync-push', 'POST', {
      entity: 'products',
      changes: changes
    });
    
    if (response.success) {
      logInfo(`Push successful: ${response.message}`);
      showCustomAlert('Success', `${response.message}`, 'success');
    } else {
      logInfo(`Push issues: ${response.errors.length} errors.`);
      if (response.staged_count === 0 && response.errors.length === 0) {
        showCustomAlert('Up to Date', 'No actual changes detected.\nValues match the database.', 'info');
      } else {
        showCustomAlert('Issues Found', `Errors: ${response.errors.length}\n${response.errors.slice(0, 3).join('\n')}`, 'error');
      }
    }
  } catch (error) {
    logInfo('Push Failed: ' + error.message);
    showCustomAlert('Push Failed', error.message, 'error');
  }
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

function fetchFromFulcrum(endpoint, method = 'GET', payload = null) {
  const config = getConfig();
  if (!config.FULCRUM_API_KEY) throw new Error('API key missing. Run Setup Connection.');
  
  const url = config.FULCRUM_API_URL + endpoint;
  const options = {
    method: method,
    headers: { 'X-API-Key': config.FULCRUM_API_KEY, 'Content-Type': 'application/json' },
    muteHttpExceptions: true
  };
  
  if (payload) options.payload = JSON.stringify(payload);
  
  const response = UrlFetchApp.fetch(url, options);
  const code = response.getResponseCode();
  
  if (code >= 400) throw new Error(`API Error ${code}: ${response.getContentText()}`);
  
  return JSON.parse(response.getContentText());
}

function getOrCreateSheet(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) sheet = ss.insertSheet(name);
  return sheet;
}

function showSyncLog() {
  const logs = getLogHistory();
  const html = HtmlService.createHtmlOutput(`
    <div style="font-family: monospace; font-size: 11px; white-space: pre-wrap; color: #333;">${logs}</div>
    <div style="margin-top: 12px; text-align: right;">
        <button onclick="clearLogs()" style="padding: 4px 8px; cursor: pointer;">Clear Log</button>
    </div>
    <script>
      function clearLogs() {
        google.script.run.withSuccessHandler(function() { google.script.host.close(); }).clearLogs();
      }
    </script>
  `)
    .setWidth(500).setHeight(300);
  SpreadsheetApp.getUi().showModalDialog(html, 'Sync Log History');
}

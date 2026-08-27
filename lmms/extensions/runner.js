/**
 * vscode API shim + extension runner for LMMs Extension Host.
 *
 * Called by:  node runner.js <manifest_path> <ext_dir> <ipc_socket>
 *
 * Communication: stdin/stdout newline-delimited JSON-RPC
 *   IN  (Python → Node):  {"id":"...", "method":"...", "params":[...]}
 *   OUT (Node → Python):  {"id":"...", "result":...} | {"method":"...", "params":[...]}
 */
'use strict';

const path    = require('path');
const fs      = require('fs');
const readline = require('readline');

// ── args ──────────────────────────────────────────────────────────────────────
const [,, manifestPath, extDir] = process.argv;

if (!manifestPath || !extDir) {
  process.stderr.write('Usage: node runner.js <manifest_path> <ext_dir>\n');
  process.exit(1);
}

// ── IPC (stdin/stdout JSON-RPC) ───────────────────────────────────────────────
const pendingRpc = new Map();   // id → {resolve, reject}
let   rpcCounter = 0;

function send(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function callPython(method, params = []) {
  return new Promise((resolve, reject) => {
    const id = String(++rpcCounter);
    pendingRpc.set(id, { resolve, reject });
    send({ id, method, params });
    setTimeout(() => {
      if (pendingRpc.has(id)) {
        pendingRpc.delete(id);
        reject(new Error(`RPC timeout: ${method}`));
      }
    }, 10000);
  });
}

// Handle Python → Node messages
const rl = readline.createInterface({ input: process.stdin, terminal: false });
rl.on('line', (line) => {
  try {
    const msg = JSON.parse(line.trim());
    if (msg.id && pendingRpc.has(msg.id)) {
      const { resolve, reject } = pendingRpc.get(msg.id);
      pendingRpc.delete(msg.id);
      if (msg.error) reject(new Error(msg.error));
      else           resolve(msg.result);
    }
    // Python-initiated calls (e.g. executeCommand, etc.)
    if (msg.method && !msg.id) {
      handleIncoming(msg).catch(e => log('error', String(e)));
    }
  } catch (_) {}
});

async function handleIncoming(msg) {
  switch (msg.method) {
    case 'executeCommand': {
      const [id, ...args] = msg.params;
      const cmd = commandRegistry.get(id);
      if (cmd) await cmd.callback(...args);
      break;
    }
  }
}

// ── Logging ───────────────────────────────────────────────────────────────────
function log(level, msg) {
  send({ method: 'log', params: { level, msg } });
}

// ── ExtensionContext ──────────────────────────────────────────────────────────
const commandRegistry = new Map();  // id → {title, callback}

const extensionContext = {
  subscriptions: [],
  extensionPath: extDir,
  extensionUri: { scheme: 'file', path: extDir, fsPath: extDir },
  globalStoragePath: path.join(process.env.HOME || '', '.lmms', 'ext_storage'),
  storagePath: path.join(process.env.HOME || '', '.lmms', 'ext_storage'),
  logPath: path.join(process.env.HOME || '', '.lmms', 'ext_logs'),
  globalState: {
    _data: {},
    get(key, def) { return this._data[key] ?? def; },
    update(key, val) { this._data[key] = val; }
  },
  workspaceState: {
    _data: {},
    get(key, def) { return this._data[key] ?? def; },
    update(key, val) { this._data[key] = val; }
  },
};

// ── vscode API ────────────────────────────────────────────────────────────────
const vscode = {

  // ── Uri ──────────────────────────────────────────────────────────────────
  Uri: {
    file: (p) => ({ scheme: 'file', path: p, fsPath: p,
                    toString: () => `file://${p}` }),
    parse: (s) => ({ scheme: s.split(':')[0], path: s, fsPath: s,
                     toString: () => s }),
    joinPath: (base, ...parts) => {
      const joined = path.join(base.fsPath, ...parts);
      return vscode.Uri.file(joined);
    },
  },

  // ── commands ──────────────────────────────────────────────────────────────
  commands: {
    registerCommand(id, callback, thisArg) {
      commandRegistry.set(id, { title: id, callback: callback.bind(thisArg) });
      send({ method: 'registerCommand', params: { id, title: id } });
      log('info', `Registered command: ${id}`);
      return { dispose: () => commandRegistry.delete(id) };
    },
    executeCommand(id, ...args) {
      // First try local
      if (commandRegistry.has(id)) {
        return Promise.resolve(commandRegistry.get(id).callback(...args));
      }
      // Ask Python
      return callPython('executeCommand', [id, ...args]);
    },
    getCommands() {
      return Promise.resolve([...commandRegistry.keys()]);
    },
  },

  // ── window ────────────────────────────────────────────────────────────────
  window: {
    showInformationMessage: (msg, ...items) =>
      callPython('window.showInformationMessage', [msg, items]),
    showWarningMessage: (msg, ...items) =>
      callPython('window.showWarningMessage', [msg, items]),
    showErrorMessage: (msg, ...items) =>
      callPython('window.showErrorMessage', [msg, items]),
    showInputBox: (opts) =>
      callPython('window.showInputBox', [opts || {}]),
    showQuickPick: (items, opts) =>
      callPython('window.showQuickPick', [items, opts || {}]),
    createOutputChannel: (name) => ({
      name,
      append:      (t) => log('output', `[${name}] ${t}`),
      appendLine:  (t) => log('output', `[${name}] ${t}`),
      show:        ()  => {},
      hide:        ()  => {},
      dispose:     ()  => {},
      clear:       ()  => {},
    }),
    createWebviewPanel: (viewType, title, showOptions, options) => {
      const panel = {
        webview: { 
          set html(val) { callPython('webview.setHtml', [viewType, val]); },
          get html() { return ''; },
          onDidReceiveMessage: () => ({dispose:()=>{}}) 
        },
        onDidDispose: () => ({dispose:()=>{}}),
        dispose: () => {},
      };
      return panel;
    },
    registerWebviewViewProvider: (viewId, provider) => {
      const webviewView = {
        webview: {
          set html(val) { callPython('webview.setHtml', [viewId, val]); },
          get html() { return ''; },
          onDidReceiveMessage: () => ({dispose:()=>{}}),
          postMessage: () => {},
        },
        onDidDispose: () => ({dispose:()=>{}}),
        onDidChangeVisibility: () => ({dispose:()=>{}}),
        visible: true,
        show: () => {}
      };
      
      // Resolve immediately to capture HTML for the native Qt DockWidget
      setTimeout(() => {
        try {
          provider.resolveWebviewView(webviewView, {}, {isCancellationRequested: false});
        } catch (e) {
          log('error', `Failed to resolve webview view ${viewId}: ${e.message}`);
        }
      }, 500);
      
      return { dispose: ()=>{} };
    },
    activeTextEditor: undefined,
    visibleTextEditors: [],
    onDidChangeActiveTextEditor: () => ({ dispose: ()=>{} }),
    withProgress: (opts, task) => task({ report: ()=>{} }, { isCancellationRequested: false }),
    createStatusBarItem: () => ({
      text: '', tooltip: '', command: '',
      show: ()=>{}, hide: ()=>{}, dispose: ()=>{}
    }),
    createTerminal: (opts) => {
      callPython('window.createTerminal', [opts || {}]);
      return {
        sendText: (t) => callPython('terminal.sendText', [t]),
        show: ()    => callPython('terminal.show', []),
        dispose: () => callPython('terminal.dispose', []),
      };
    },
  },

  // ── workspace ─────────────────────────────────────────────────────────────
  workspace: {
    get workspaceFolders() {
      return undefined;  // overridden async below
    },
    name: undefined,
    getConfiguration: (section) => ({
      get: (key, def) => def,
      has: (key)      => false,
      update: (key, val) => callPython('workspace.updateConfiguration', [section, key, val]),
      inspect: (key) => undefined,
    }),
    openTextDocument: (uri) =>
      callPython('workspace.openTextDocument', [typeof uri === 'string' ? uri : uri?.fsPath || uri?.path]),
    onDidChangeWorkspaceFolders: () => ({ dispose: ()=>{} }),
    onDidOpenTextDocument: () => ({ dispose: ()=>{} }),
    onDidCloseTextDocument: () => ({ dispose: ()=>{} }),
    onDidSaveTextDocument: () => ({ dispose: ()=>{} }),
    onDidChangeTextDocument: () => ({ dispose: ()=>{} }),
    findFiles: (include, exclude) =>
      callPython('workspace.findFiles', [include, exclude]),
    saveAll: () => Promise.resolve(true),
    fs: {
      readFile:   (uri) => callPython('fs.readFile',   [uri?.fsPath || uri]),
      writeFile:  (uri, content) => callPython('fs.writeFile', [uri?.fsPath || uri, Array.from(content)]),
      stat:       (uri) => callPython('fs.stat', [uri?.fsPath || uri]),
      readDirectory:(uri) => callPython('fs.readDirectory', [uri?.fsPath || uri]),
      createDirectory:(uri) => callPython('fs.createDirectory', [uri?.fsPath || uri]),
      delete:     (uri) => callPython('fs.delete', [uri?.fsPath || uri]),
      rename:     (src, dst) => callPython('fs.rename', [src?.fsPath||src, dst?.fsPath||dst]),
    },
  },

  // ── languages ─────────────────────────────────────────────────────────────
  languages: {
    registerCompletionItemProvider: (selector, provider) => {
      log('info', `Registered completion provider for: ${JSON.stringify(selector)}`);
      return { dispose: ()=>{} };
    },
    registerHoverProvider: (selector, provider) => {
      log('info', `Registered hover provider for: ${JSON.stringify(selector)}`);
      return { dispose: ()=>{} };
    },
    createDiagnosticCollection: (name) => ({
      name,
      set: ()=>{}, delete: ()=>{}, clear: ()=>{}, dispose: ()=>{}, has: ()=>false,
    }),
    registerDocumentFormattingEditProvider: () => ({ dispose:()=>{} }),
    registerDefinitionProvider: () => ({ dispose:()=>{} }),
    registerCodeActionsProvider: () => ({ dispose:()=>{} }),
    registerSignatureHelpProvider: () => ({ dispose:()=>{} }),
    registerReferenceProvider: () => ({ dispose:()=>{} }),
    registerRenameProvider: () => ({ dispose:()=>{} }),
    getDiagnostics: () => [],
    setLanguageConfiguration: () => ({ dispose:()=>{} }),
  },

  // ── env ───────────────────────────────────────────────────────────────────
  env: {
    appName: 'LMMs Editor',
    appRoot: extDir,
    language: 'en',
    uiKind:   1,   // UIKind.Desktop
    openExternal: (uri) => callPython('env.openExternal', [String(uri)]),
    clipboard: {
      readText:  () => callPython('env.clipboard.readText', []),
      writeText: (t) => callPython('env.clipboard.writeText', [t]),
    },
  },

  // ── extensions ────────────────────────────────────────────────────────────
  extensions: {
    getExtension: (id) => null,
    all: [],
  },

  // ── Common classes / enums ────────────────────────────────────────────────
  Range: class { constructor(sl,sc,el,ec){this.start={line:sl,character:sc};this.end={line:el,character:ec};} },
  Position: class { constructor(l,c){this.line=l;this.character=c;} },
  Location: class { constructor(uri,rng){this.uri=uri;this.range=rng;} },
  Selection: class { constructor(al,ac,ac2,ac3){} },
  Hover: class { constructor(contents){this.contents=contents;} },
  CompletionItem: class { constructor(label,kind){this.label=label;this.kind=kind;} },
  DiagnosticSeverity: { Error:0, Warning:1, Information:2, Hint:3 },
  Diagnostic: class { constructor(range,msg,severity){this.range=range;this.message=msg;this.severity=severity;} },
  StatusBarAlignment: { Left:1, Right:2 },
  CompletionItemKind: { Text:0, Method:1, Function:2, Constructor:3, Field:4, Variable:5, Class:6, Interface:7, Module:8, Property:9, Unit:10, Value:11, Enum:12, Keyword:13, Snippet:14, Color:15, File:16, Reference:17, Folder:18, EnumMember:19, Constant:20, Struct:21, Event:22, Operator:23, TypeParameter:24 },
  TreeItemCollapsibleState: { None:0, Collapsed:1, Expanded:2 },
  ThemeIcon: class { constructor(id){this.id=id;} },
  EventEmitter: class {
    constructor() { this.listeners = []; }
    event(l) { this.listeners.push(l); return ()=>{ this.listeners = this.listeners.filter(x=>x!==l); }; }
    fire(data) { this.listeners.forEach(l=>l(data)); }
    dispose() { this.listeners = []; }
  },
  Disposable: class {
    constructor(fn) { this._fn = fn; }
    dispose() { this._fn(); }
    static from(...items) { return new vscode.Disposable(()=>items.forEach(i=>i.dispose())); }
  },
  CancellationTokenSource: class {
    constructor() {
      this.token = { isCancellationRequested: false, onCancellationRequested: ()=>({dispose:()=>{}}) };
    }
    cancel() { this.token.isCancellationRequested = true; }
    dispose() {}
  },
  ProgressLocation: { SourceControl:1, Window:10, Notification:15 },
  ViewColumn: { One:1, Two:2, Three:3, Active:-1, Beside:-2 },
  EndOfLine: { LF:1, CRLF:2 },
  FileType: { Unknown:0, File:1, Directory:2, SymbolicLink:64 },
  QuickPickItemKind: { Default:0, Separator:-1 },
  OverviewRulerLane: { Left:1, Center:2, Right:4, Full:7 },
  DecorationRangeBehavior: { OpenOpen:0, ClosedClosed:1, OpenClosed:2, ClosedOpen:3 },
  ConfigurationTarget: { Global: 1, Workspace: 2, WorkspaceFolder: 3 },
  UIKind: { Desktop: 1, Web: 2 },
};

// ── Require hook — intercept "vscode" module ──────────────────────────────────
const Module = require('module');
const _origLoad = Module._load;
Module._load = function(request, parent, isMain) {
  if (request === 'vscode') return vscode;
  return _origLoad.call(this, request, parent, isMain);
};

// ── Load and activate extension ───────────────────────────────────────────────
async function main() {
  let manifest;
  try {
    manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
  } catch (e) {
    log('error', `Cannot read manifest: ${e.message}`);
    process.exit(1);
  }

  const mainEntry = manifest.main || manifest.browser;
  if (!mainEntry) {
    log('warn', 'No main entry point — extension has no JS to activate.');
    send({ method: 'activated', params: { commands: [] } });
    return;
  }

  const mainPath = path.resolve(extDir, 'extension', mainEntry.replace(/^\.\//, ''));
  if (!fs.existsSync(mainPath)) {
    log('error', `Main file not found: ${mainPath}`);
    send({ method: 'activationFailed', params: { error: `main file not found: ${mainPath}` } });
    process.exit(1);
  }

  log('info', `Activating: ${mainPath}`);

  try {
    // Populate workspace folders via IPC before activation
    callPython('workspace.getFolders', []).then(folders => {
      if (folders) vscode.workspace.workspaceFolders = folders;
    }).catch(()=>{});

    const ext = require(mainPath);
    if (typeof ext.activate === 'function') {
      await ext.activate(extensionContext);
      const cmds = [...commandRegistry.keys()];
      log('info', `✓ Activated — ${cmds.length} command(s) registered: ${cmds.join(', ')}`);
      send({ method: 'activated', params: { commands: cmds } });
    } else {
      log('warn', 'Extension has no activate() export.');
      send({ method: 'activated', params: { commands: [] } });
    }
  } catch (e) {
    log('error', `Activation error: ${e.stack || e.message}`);
    send({ method: 'activationFailed', params: { error: String(e.stack || e.message) } });
    process.exit(1);
  }
}

main().catch(e => {
  log('error', String(e));
  process.exit(1);
});

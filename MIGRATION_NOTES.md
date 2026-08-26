# LMMs Engine Upgrade - Migration Notes

## Dependencies Pinning
For the Monaco editor to correctly integrate with the VS Code extension host and Command Palette without backend discrepancies, the `@codingame/monaco-vscode-api` and its service overrides were pinned to `~8.0.4`.

### Installed Services:
- `@codingame/monaco-vscode-api@~8.0.4`
- `@codingame/monaco-vscode-base-service-override@~8.0.4`
- `@codingame/monaco-vscode-environment-service-override@~8.0.4`
- `@codingame/monaco-vscode-extensions-service-override@~8.0.4`
- `@codingame/monaco-vscode-files-service-override@~8.0.4`
- `@codingame/monaco-vscode-host-service-override@~8.0.4`
- `@codingame/monaco-vscode-languages-service-override@~8.0.4`
- `@codingame/monaco-vscode-layout-service-override@~8.0.4`
- `@codingame/monaco-vscode-localization-service-override@~8.0.4`
- `@codingame/monaco-vscode-model-service-override@~8.0.4`
- `@codingame/monaco-vscode-quickaccess-service-override@~8.0.4`

## Initialization
The `vscode/services` `initialize` function is now called before `monaco.editor.create`. Top-level await is enabled in Vite (`target: 'es2022'`).

## Command Palette
F1 functionality is now active, hooking into VS Code's native `quickaccess` and `layout` services.

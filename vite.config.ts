import { readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import type { Plugin } from 'vite'
import { defineConfig } from 'vite'

const siteRoot = dirname(fileURLToPath(import.meta.url))
const parqdbRoot = resolve(process.env.PARQDB_ROOT ?? resolve(siteRoot, '../parqdb'))
const browserRoot = resolve(parqdbRoot, 'browser')
const wasmPath = resolve(
  parqdbRoot,
  'target/wasm32-unknown-unknown/release/parqdb_browser_kernels.wasm',
)

function parqdbWasm(): Plugin {
  return {
    name: 'parqdb-wasm',
    async generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'parqdb_browser_kernels.wasm',
        source: await readFile(wasmPath),
      })
    },
  }
}

export default defineConfig({
  root: siteRoot,
  base: './',
  publicDir: resolve(siteRoot, 'public'),
  resolve: {
    alias: {
      '@parqdb/index': resolve(browserRoot, 'src/index.ts'),
      '@parqdb/http': resolve(browserRoot, 'src/http.ts'),
    },
  },
  plugins: [parqdbWasm()],
  build: {
    outDir: resolve(siteRoot, 'dist'),
    emptyOutDir: true,
    target: 'es2022',
  },
})

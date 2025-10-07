import { playwrightLauncher } from '@web/test-runner-playwright';
import { fromRollup } from '@web/dev-server-rollup';
import rollupCommonjs from '@rollup/plugin-commonjs';
import rollupReplace from '@rollup/plugin-replace';

const commonjs = fromRollup(rollupCommonjs);
const replace = fromRollup(rollupReplace);

export default {
  browsers: [
    playwrightLauncher({
      product: 'chromium',
      launchOptions: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
      },
    }),
  ],
  testFramework: {
    // we are using jasmine, so we don't need to configure anything here
  },
  plugins: [
    commonjs({
      include: ['**/node_modules/rxjs/**/*'],
    }),
    replace({
      preventAssignment: true,
      values: {
        'process.env.NODE_ENV': JSON.stringify('production'),
      },
    }),
  ],
  files: ['./dist/test-out/**/*.spec.js'],
  nodeResolve: true,
};

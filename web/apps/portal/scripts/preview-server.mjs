/**
 * PlannedEducation - Headless Production Preview Server
 * Programmatic HTTP preview server using Vite's native API.
 * Runs cleanly in both background/daemon modes and interactive sessions.
 */
import { preview } from 'vite';

const port = parseInt(process.env.FRONTEND_PORT || process.argv[2] || '5173', 10);
const host = process.env.HOST || '0.0.0.0';

process.on('SIGHUP', () => {});

try {
  const server = await preview({
    preview: {
      port,
      host
    }
  });
  server.printUrls();
} catch (err) {
  console.error('[ERROR] Failed to start preview server:', err);
  process.exit(1);
}

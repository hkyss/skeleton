<?php

declare(strict_types=1);

$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';

if ($path === '/health') {
    http_response_code(204);
    exit;
}

header('Content-Type: text/html; charset=utf-8');

echo '<!doctype html>';
echo '<html lang="en">';
echo '<head>';
echo '<meta charset="utf-8">';
echo '<title>Legacy PHP + Vite Preset</title>';
echo '<script type="module" src="/theme/dist/main.js"></script>';
echo '</head>';
echo '<body>';
echo '<div id="app">Legacy PHP + Vite preset is running</div>';
echo '</body>';
echo '</html>';

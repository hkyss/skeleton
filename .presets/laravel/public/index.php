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
echo '<head><meta charset="utf-8"><title>Laravel Preset</title></head>';
echo '<body>';
echo '<h1>Laravel-style preset is running</h1>';
echo '<p>Replace this minimal front controller with a real Laravel application.</p>';
echo '</body>';
echo '</html>';

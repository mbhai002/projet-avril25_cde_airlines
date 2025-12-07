<?php
/**
 * Serveur de réponses HTML brutes pour airportinfo
 * Permet de servir les fichiers HTML collectés sans passer par Cloudflare
 */

header('Content-Type: text/html; charset=utf-8');
header('Access-Control-Allow-Origin: *');

// Configuration
define('DATA_DIR', __DIR__ . '/data/');
define('MAX_AGE_HOURS', 24); // Âge maximum des fichiers acceptés

// Récupérer les paramètres
$iataAirport = $_POST['iataAirport'] ?? $_GET['iataAirport'] ?? '';
$depArr = $_POST['depArr'] ?? $_GET['depArr'] ?? 'departure';
$date = $_POST['date'] ?? $_GET['date'] ?? date('Y-m-d');
$shift = $_POST['shift'] ?? $_GET['shift'] ?? '00';

// Validation des paramètres
if (empty($iataAirport) || !preg_match('/^[A-Z]{3}$/', $iataAirport)) {
    http_response_code(400);
    die('Invalid airport code');
}

if (!in_array($depArr, ['arrival', 'departure'])) {
    http_response_code(400);
    die('Invalid depArr parameter');
}

if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $date)) {
    http_response_code(400);
    die('Invalid date format');
}

if (!preg_match('/^\d{2}$/', $shift)) {
    http_response_code(400);
    die('Invalid shift format');
}

// Chercher le fichier le plus récent correspondant
$pattern = sprintf(
    'raw_%s_%s_%s_%sh_*.html',
    $iataAirport,
    $depArr,
    $date,
    $shift
);

$files = glob(DATA_DIR . $pattern);

if (empty($files)) {
    http_response_code(404);
    die('No data found for this request');
}

// Trier par date de modification (plus récent en premier)
usort($files, function($a, $b) {
    return filemtime($b) - filemtime($a);
});

$file = $files[0];

// Vérifier l'âge du fichier
$fileAge = time() - filemtime($file);
$maxAge = MAX_AGE_HOURS * 3600;

if ($fileAge > $maxAge) {
    http_response_code(410);
    die('Data too old');
}

// Ajouter des headers pour informer sur l'âge des données
header('X-Data-Age-Seconds: ' . $fileAge);
header('X-Data-Age-Minutes: ' . round($fileAge / 60));
header('X-Source-File: ' . basename($file));
header('X-File-Modified: ' . date('Y-m-d H:i:s', filemtime($file)));

// Servir le fichier
readfile($file);

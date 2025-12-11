<?php
/**
 * API de listing des fichiers disponibles
 * Permet de voir quels aéroports/dates/heures sont disponibles
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

define('DATA_DIR', __DIR__ . '/data/');

// Paramètres optionnels de filtrage
$airport = $_GET['airport'] ?? null;
$date = $_GET['date'] ?? null;
$depArr = $_GET['depArr'] ?? null;

// Scanner les fichiers
$pattern = DATA_DIR . 'raw_*.html';
$files = glob($pattern);

$results = [];

foreach ($files as $file) {
    $basename = basename($file);
    
    // Parser le nom du fichier: raw_IATA_depArr_DATE_SHIFTh_TIMESTAMP.html
    if (preg_match('/^raw_([A-Z]{3})_(arrival|departure)_(\d{4}-\d{2}-\d{2})_(\d{2})h_(\d{8}_\d{6})\.html$/', $basename, $matches)) {
        $fileInfo = [
            'filename' => $basename,
            'airport' => $matches[1],
            'type' => $matches[2],
            'date' => $matches[3],
            'shift' => $matches[4],
            'timestamp' => $matches[5],
            'size' => filesize($file),
            'modified' => date('Y-m-d H:i:s', filemtime($file)),
            'age_hours' => round((time() - filemtime($file)) / 3600, 1)
        ];
        
        // Appliquer les filtres
        if ($airport && $fileInfo['airport'] !== strtoupper($airport)) continue;
        if ($date && $fileInfo['date'] !== $date) continue;
        if ($depArr && $fileInfo['type'] !== $depArr) continue;
        
        $results[] = $fileInfo;
    }
}

// Trier par date de modification (plus récent en premier)
usort($results, function($a, $b) {
    return strcmp($b['timestamp'], $a['timestamp']);
});

// Statistiques
$stats = [
    'total_files' => count($results),
    'airports' => array_unique(array_column($results, 'airport')),
    'dates' => array_unique(array_column($results, 'date')),
    'oldest_file_age_hours' => !empty($results) ? max(array_column($results, 'age_hours')) : 0,
    'newest_file_age_hours' => !empty($results) ? min(array_column($results, 'age_hours')) : 0,
];

echo json_encode([
    'status' => 'success',
    'stats' => $stats,
    'files' => $results
], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);

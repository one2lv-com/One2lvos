<?php
/*
 * One2lvOS IONOS diagnostics API (read-only)
 * - Every request needs the header  X-Diag-Token: <token>
 * - The token lives outside the web folder in /.diag_private/config.php
 * - No shell commands, no file writes, no phpinfo, no environment dump.
 * Actions: ping, env, htaccess, dns, index, http, ssl, sftp, recent, all
 */
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
header('X-Robots-Tag: noindex, nofollow');

const WEB_LABEL   = '/one2lvos';
const SITE_HOST   = 's1086212999.onlinehome.us';
const SFTP_HOST   = 'access-5019872554.webspace-host.com';
const DOMAIN      = 'one2lv.com';

$WEB_ROOT   = dirname(__DIR__);                 // .../htdocs/one2lvos
$SPACE_ROOT = dirname(__DIR__, 2);              // .../htdocs (not served by the onlinehome host)
$PRIV_DIR   = $SPACE_ROOT . '/.diag_private';

function out(array $data, int $code = 200): void {
    http_response_code($code);
    echo json_encode($data, JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
    exit;
}

/* ── Auth ─────────────────────────────────────────────────────────────── */
$cfgFile = $PRIV_DIR . '/config.php';
$cfg = is_readable($cfgFile) ? (include $cfgFile) : null;
$expected = (is_array($cfg) && !empty($cfg['token'])) ? (string)$cfg['token'] : '';
$given = (string)($_SERVER['HTTP_X_DIAG_TOKEN'] ?? '');
if ($expected === '') {
    out(['ok' => false, 'error' => 'not_configured'], 503);
}
if ($given === '' || !hash_equals($expected, $given)) {
    usleep(400000);
    out(['ok' => false, 'error' => 'unauthorized', 'hint' => 'send the X-Diag-Token header'], 401);
}

/* ── Helpers ──────────────────────────────────────────────────────────── */
function rel(string $path, string $root): string {
    $r = substr($path, strlen($root));
    return WEB_LABEL . ($r === '' ? '/' : $r);
}
function iso(int $ts): string { return gmdate('c', $ts); }
function walk(string $root): array {
    $files = [];
    $it = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($root, FilesystemIterator::SKIP_DOTS),
        RecursiveIteratorIterator::SELF_FIRST
    );
    foreach ($it as $f) {
        if ($f->isLink() || !$f->isFile()) continue;
        $files[] = [$f->getPathname(), $f->getSize(), $f->getMTime()];
    }
    return $files;
}
function human(float $b): string {
    $u = ['B','KB','MB','GB','TB']; $i = 0;
    while ($b >= 1024 && $i < 4) { $b /= 1024; $i++; }
    return round($b, $i ? 2 : 0) . ' ' . $u[$i];
}

/* ── Checks ───────────────────────────────────────────────────────────── */
function check_env(string $root): array {
    $files = walk($root);
    $bytes = 0; foreach ($files as $f) $bytes += $f[1];
    $free  = function_exists('disk_free_space')  ? @disk_free_space($root)  : false;
    $total = function_exists('disk_total_space') ? @disk_total_space($root) : false;
    return [
        'php_version'     => PHP_VERSION,
        'sapi'            => PHP_SAPI,
        'server_software' => (string)($_SERVER['SERVER_SOFTWARE'] ?? 'unknown'),
        'os_family'       => PHP_OS_FAMILY,
        'https'           => (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off'),
        'web_root'        => WEB_LABEL . ' (served as /one2lv.com)',
        'web_files'       => count($files),
        'web_bytes'       => $bytes,
        'web_size'        => human((float)$bytes),
        'volume_free'     => $free === false ? null : human((float)$free),
        'volume_total'    => $total === false ? null : human((float)$total),
        'volume_note'     => 'shared hosting volume, not the plan quota',
        'extensions'      => [
            'curl'    => function_exists('curl_init'),
            'openssl' => extension_loaded('openssl'),
            'mbstring'=> extension_loaded('mbstring'),
            'pdo'     => extension_loaded('pdo'),
        ],
        'memory_limit'    => ini_get('memory_limit'),
        'max_upload'      => ini_get('upload_max_filesize'),
        'server_time'     => iso(time()),
    ];
}

function sanitize_line(string $l): string {
    if (preg_match('/(pass|secret|token|apikey|api_key|key=|AuthUserFile|AuthGroupFile)/i', $l)) {
        return preg_replace('/^(\s*\S+).*/', '$1 [redacted]', $l);
    }
    return preg_replace('#/homepages/[^\s"\']*#', '[path]', $l);
}
function check_htaccess(string $root): array {
    $out = [];
    foreach (['' => $root . '/.htaccess', 'diagnostics' => __DIR__ . '/.htaccess'] as $k => $p) {
        $label = WEB_LABEL . ($k ? "/$k" : '') . '/.htaccess';
        if (!is_file($p)) { $out[] = ['file' => $label, 'exists' => false]; continue; }
        $lines = preg_split('/\r?\n/', (string)file_get_contents($p, false, null, 0, 20000));
        $out[] = [
            'file' => $label, 'exists' => true, 'bytes' => filesize($p), 'modified' => iso(filemtime($p)),
            'lines' => array_values(array_map('sanitize_line', array_filter($lines, fn($l) => trim($l) !== ''))),
        ];
    }
    return ['files' => $out];
}

function check_dns(): array {
    $hosts = [DOMAIN, 'www.' . DOMAIN, 'mail.' . DOMAIN, SITE_HOST, SFTP_HOST];
    $res = [];
    foreach ($hosts as $h) {
        $a = @dns_get_record($h, DNS_A) ?: [];
        $aaaa = @dns_get_record($h, DNS_AAAA) ?: [];
        $cname = @dns_get_record($h, DNS_CNAME) ?: [];
        $res[$h] = [
            'a'     => array_values(array_map(fn($r) => $r['ip'], $a)),
            'aaaa'  => array_values(array_map(fn($r) => $r['ipv6'], $aaaa)),
            'cname' => array_values(array_map(fn($r) => $r['target'], $cname)),
            'gethostbyname' => ($ip = gethostbyname($h)) === $h ? null : $ip,
        ];
    }
    $mx = @dns_get_record(DOMAIN, DNS_MX) ?: [];
    $ns = @dns_get_record(DOMAIN, DNS_NS) ?: [];
    return [
        'hosts' => $res,
        'mx' => array_values(array_map(fn($r) => ['host' => $r['target'], 'pri' => $r['pri']], $mx)),
        'ns' => array_values(array_map(fn($r) => $r['target'], $ns)),
    ];
}

function check_index(string $root): array {
    $out = [];
    foreach (['', '/diagnostics'] as $d) {
        foreach (['index.html', 'index.php'] as $n) {
            $p = $root . $d . '/' . $n;
            $out[] = is_file($p)
                ? ['file' => WEB_LABEL . "$d/$n", 'exists' => true, 'bytes' => filesize($p), 'modified' => iso(filemtime($p))]
                : ['file' => WEB_LABEL . "$d/$n", 'exists' => false];
        }
    }
    return ['files' => $out];
}

function probe(string $url): array {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_NOBODY => true, CURLOPT_RETURNTRANSFER => true, CURLOPT_HEADER => true,
        CURLOPT_FOLLOWLOCATION => false, CURLOPT_TIMEOUT => 10, CURLOPT_CONNECTTIMEOUT => 6,
        CURLOPT_USERAGENT => 'One2lvOS-Diagnostics/1.0', CURLOPT_SSL_VERIFYPEER => true,
    ]);
    $t = microtime(true);
    $raw = curl_exec($ch);
    $ms = (int)round((microtime(true) - $t) * 1000);
    $err = curl_error($ch);
    $code = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    $method = 'HEAD';
    if ($code === 405 || $code === 501) {          // HEAD not allowed: retry with GET
        curl_setopt_array($ch, [CURLOPT_NOBODY => false, CURLOPT_HTTPGET => true]);
        $t = microtime(true);
        $raw = curl_exec($ch);
        $ms = (int)round((microtime(true) - $t) * 1000);
        $err = curl_error($ch);
        $code = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $method = 'GET';
        if (is_string($raw)) { $hs = (int)curl_getinfo($ch, CURLINFO_HEADER_SIZE); $raw = substr($raw, 0, $hs); }
    }
    $ip = (string)curl_getinfo($ch, CURLINFO_PRIMARY_IP);
    $hdr = [];
    if (is_string($raw)) {
        foreach (preg_split('/\r?\n/', $raw) as $l) {
            if (preg_match('/^(server|location|cf-ray|content-type):\s*(.+)$/i', $l, $m)) $hdr[strtolower($m[1])] = trim($m[2]);
        }
    }
    $loc = $hdr['location'] ?? null;
    if ($loc !== null) { $loc = preg_replace('/[?#].*$/', '', $loc); }
    return ['url' => $url, 'status' => $code ?: null, 'latency_ms' => $ms, 'ip' => $ip ?: null,
            'server' => $hdr['server'] ?? null, 'location' => $loc,
            'cloudflare' => isset($hdr['cf-ray']), 'method' => $method, 'error' => $err ?: null];
}
function check_http(): array {
    return ['probes' => [
        probe('http://' . SITE_HOST . '/'),
        probe('http://' . SITE_HOST . '/diagnostics/'),
        probe('http://' . DOMAIN . '/'),
        probe('https://' . DOMAIN . '/'),
    ]];
}

function tls(string $host): array {
    $ctx = stream_context_create(['ssl' => [
        'capture_peer_cert' => true, 'verify_peer' => false, 'verify_peer_name' => false, 'SNI_enabled' => true, 'peer_name' => $host,
    ]]);
    $tcp = @fsockopen($host, 443, $tn, $ts, 6);
    $portOpen = (bool)$tcp; if ($tcp) fclose($tcp);
    $t = microtime(true);
    while (openssl_error_string() !== false) {}
    $s = @stream_socket_client("ssl://$host:443", $errno, $errstr, 8, STREAM_CLIENT_CONNECT, $ctx);
    $ms = (int)round((microtime(true) - $t) * 1000);
    if (!$s) {
        $ossl = openssl_error_string();
        $why = $portOpen ? 'port 443 open but the TLS handshake failed (no certificate served for this host)' : 'port 443 closed';
        return ['host' => $host, 'connects' => false, 'port_443_open' => $portOpen, 'latency_ms' => $ms,
                'error' => $why . ($ossl ? " [$ossl]" : ($errstr ? " [$errstr]" : ''))];
    }
    $p = stream_context_get_params($s);
    fclose($s);
    $c = @openssl_x509_parse($p['options']['ssl']['peer_certificate'] ?? '');
    if (!$c) return ['host' => $host, 'connects' => true, 'latency_ms' => $ms, 'certificate' => null];
    $san = (string)($c['extensions']['subjectAltName'] ?? '');
    $names = array_map(fn($x) => trim(str_replace('DNS:', '', $x)), array_filter(explode(',', $san)));
    $match = false;
    foreach ($names as $n) {
        if (strcasecmp($n, $host) === 0) $match = true;
        if (str_starts_with($n, '*.') && strcasecmp(substr($n, 1), substr($host, strpos($host, '.'))) === 0) $match = true;
    }
    // verified handshake (chain + name)
    $vctx = stream_context_create(['ssl' => ['verify_peer' => true, 'verify_peer_name' => true, 'SNI_enabled' => true, 'peer_name' => $host]]);
    $v = @stream_socket_client("ssl://$host:443", $e2, $s2, 8, STREAM_CLIENT_CONNECT, $vctx);
    if ($v) fclose($v);
    return [
        'host' => $host, 'connects' => true, 'latency_ms' => $ms,
        'valid_for_host' => (bool)$v, 'name_matches' => $match,
        'certificate' => [
            'subject_cn' => $c['subject']['CN'] ?? null,
            'issuer'     => trim(($c['issuer']['O'] ?? '') . ' ' . ($c['issuer']['CN'] ?? '')),
            'valid_from' => iso((int)$c['validFrom_time_t']),
            'valid_to'   => iso((int)$c['validTo_time_t']),
            'san'        => array_slice(array_values($names), 0, 12),
        ],
    ];
}
function check_ssl(): array {
    return ['targets' => [tls(SITE_HOST), tls(DOMAIN)]];
}

function check_sftp(string $priv): array {
    $t = microtime(true);
    $s = @fsockopen(SFTP_HOST, 22, $errno, $errstr, 6);
    $ms = (int)round((microtime(true) - $t) * 1000);
    $banner = null;
    if ($s) { stream_set_timeout($s, 4); $banner = trim((string)fgets($s, 256)); fclose($s); }
    $last = null;
    $lf = $priv . '/last_sftp_check.json';
    if (is_readable($lf)) {
        $j = json_decode((string)file_get_contents($lf, false, null, 0, 8000), true);
        if (is_array($j)) $last = $j;
    }
    return [
        'port_22' => ['host' => SFTP_HOST, 'reachable' => (bool)$s, 'latency_ms' => $ms,
                      'banner' => $banner, 'ssh' => $banner !== null && str_starts_with($banner, 'SSH-'),
                      'error' => $s ? null : ($errstr ?: "errno $errno")],
        'last_reactor_login' => $last,
    ];
}

function check_recent(string $root, int $n = 12): array {
    $files = walk($root);
    usort($files, fn($a, $b) => $b[2] <=> $a[2]);
    return ['files' => array_map(fn($f) => ['file' => rel($f[0], $root), 'bytes' => $f[1], 'modified' => iso($f[2])],
                                 array_slice($files, 0, $n))];
}

/* ── Router ───────────────────────────────────────────────────────────── */
$action = strtolower((string)($_GET['action'] ?? 'ping'));
$t0 = microtime(true);
switch ($action) {
    case 'ping':     $data = ['pong' => true, 'server_time' => iso(time())]; break;
    case 'env':      $data = check_env($WEB_ROOT); break;
    case 'htaccess': $data = check_htaccess($WEB_ROOT); break;
    case 'dns':      $data = check_dns(); break;
    case 'index':    $data = check_index($WEB_ROOT); break;
    case 'http':     $data = check_http(); break;
    case 'ssl':      $data = check_ssl(); break;
    case 'sftp':     $data = check_sftp($PRIV_DIR); break;
    case 'recent':   $data = check_recent($WEB_ROOT); break;
    case 'all':
        $data = [
            'env' => check_env($WEB_ROOT), 'htaccess' => check_htaccess($WEB_ROOT), 'dns' => check_dns(),
            'index' => check_index($WEB_ROOT), 'http' => check_http(), 'ssl' => check_ssl(), 'sftp' => check_sftp($PRIV_DIR),
        ];
        break;
    default:
        out(['ok' => false, 'error' => 'unknown_action',
             'actions' => ['ping','env','htaccess','dns','index','http','ssl','sftp','recent','all']], 400);
}
out(['ok' => true, 'action' => $action, 'took_ms' => (int)round((microtime(true) - $t0) * 1000), 'data' => $data]);

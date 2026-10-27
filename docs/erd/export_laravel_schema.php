<?php
// Usage: php export_laravel_schema.php /absolute/laravel/repository /absolute/output.json
// Uses only a fresh in-memory test database; never migrates the configured application database.
if ($argc !== 3) { fwrite(STDERR, "Usage: php export_laravel_schema.php LARAVEL_ROOT OUTPUT_JSON\n"); exit(1); }
$root = realpath($argv[1]);
if (! $root || ! is_file($root.'/bootstrap/app.php')) { throw new RuntimeException('Invalid Laravel root'); }
putenv('APP_ENV=testing');
$_ENV['APP_ENV'] = $_SERVER['APP_ENV'] = 'testing';
require $root.'/vendor/autoload.php';
$app = require $root.'/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$app->detectEnvironment(fn () => 'testing');
config(['database.default'=>'sqlite', 'database.connections.sqlite.database'=>':memory:', 'database.connections.sqlite.url'=>null, 'cache.default'=>'array']);
Illuminate\Support\Facades\DB::purge('sqlite');
$conn = Illuminate\Support\Facades\DB::connection('sqlite');
if ($conn->getDriverName() !== 'sqlite' || $conn->getDatabaseName() !== ':memory:' || ! $app->environment('testing')) {
    throw new RuntimeException('Expected isolated in-memory testing database');
}
$exit = Illuminate\Support\Facades\Artisan::call('migrate', ['--force'=>true]);
fwrite(STDERR, Illuminate\Support\Facades\Artisan::output());
if ($exit !== 0) { exit($exit); }
$schema = $conn->getSchemaBuilder();
$output = [];
foreach ($schema->getTables() as $table) {
    $name = $table['name'];
    $output[$name] = ['columns'=>$schema->getColumns($name), 'indexes'=>array_values($schema->getIndexes($name)), 'foreign_keys'=>$schema->getForeignKeys($name)];
}
file_put_contents($argv[2], json_encode($output, JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR));
fwrite(STDERR, 'Exported '.count($output)." tables from isolated test database.\n");

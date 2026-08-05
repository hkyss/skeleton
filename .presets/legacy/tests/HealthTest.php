<?php

declare(strict_types=1);

namespace Tests;

use PHPUnit\Framework\TestCase;

final class HealthTest extends TestCase
{
    public function testHealthEndpointAndFrontendAssetContractAreDocumented(): void
    {
        $frontController = file_get_contents(__DIR__ . '/../public/index.php');

        self::assertIsString($frontController);
        self::assertStringContainsString("http_response_code(204)", $frontController);
        self::assertStringContainsString("/theme/dist/main.js", $frontController);
    }
}

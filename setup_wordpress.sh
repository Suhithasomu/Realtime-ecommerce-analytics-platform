#!/bin/bash
echo "Setting up WordPress correctly..."

# Wait for WordPress to be ready
sleep 10

# Install WooCommerce
docker compose exec wordpress wp plugin install woocommerce --activate --allow-root

# Enable WooCommerce API
docker compose exec wordpress wp eval '
update_option("woocommerce_api_enabled", "yes");
update_option("permalink_structure", "/%postname%/");
flush_rewrite_rules();

global $wpdb;
$wpdb->query("DELETE FROM wp_woocommerce_api_keys");
$ck = "ck_myproject2026";
$cs = "cs_myproject2026";
$wpdb->insert("wp_woocommerce_api_keys", array(
    "user_id" => 1,
    "description" => "MyProject",
    "permissions" => "read_write",
    "consumer_key" => wc_api_hash($ck),
    "consumer_secret" => $cs,
    "truncated_key" => substr($ck, -7)
));
echo "Done!\n";
' --allow-root

echo "✅ WordPress setup complete!"
echo "Key: ck_myproject2026"
echo "Secret: cs_myproject2026"

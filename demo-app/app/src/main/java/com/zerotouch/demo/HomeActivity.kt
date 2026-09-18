package com.zerotouch.demo

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity

class HomeActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)

        // Profile button
        findViewById<Button>(R.id.btn_profile).setOnClickListener {
            startActivity(Intent(this, ProfileActivity::class.java))
        }

        // Search entry container
        findViewById<View>(R.id.btn_search).setOnClickListener {
            startActivity(Intent(this, SearchActivity::class.java))
        }

        // Product Cards
        findViewById<View>(R.id.card_product_1).setOnClickListener {
            openProduct(
                name = "Wireless Headphones",
                price = "$129.99",
                rating = "★ 4.5 / 5.0",
                description = "High-fidelity audio with active noise cancellation and 35-hour battery life."
            )
        }

        findViewById<View>(R.id.card_product_2).setOnClickListener {
            openProduct(
                name = "Smart Watch Pro",
                price = "$249.99",
                rating = "★ 4.8 / 5.0",
                description = "Advanced fitness tracking, AMOLED touch display, and heart-rate monitoring."
            )
        }

        findViewById<View>(R.id.card_product_3).setOnClickListener {
            openProduct(
                name = "Noise Cancelling Earbuds",
                price = "$89.99",
                rating = "★ 4.3 / 5.0",
                description = "Pocket-sized true wireless earbuds with custom dynamic sound drivers."
            )
        }

        findViewById<View>(R.id.card_product_4).setOnClickListener {
            openProduct(
                name = "Mechanical Keyboard",
                price = "$119.50",
                rating = "★ 4.7 / 5.0",
                description = "Custom hot-swappable tactile switches, aluminum top frame, and RGB backlight."
            )
        }

        findViewById<View>(R.id.card_product_5).setOnClickListener {
            openProduct(
                name = "Ultra-wide Gaming Monitor",
                price = "$499.00",
                rating = "★ 4.6 / 5.0",
                description = "34-inch curved ultra-wide QHD display with 144Hz refresh rate."
            )
        }

        findViewById<View>(R.id.card_product_6).setOnClickListener {
            openProduct(
                name = "Portable Bluetooth Speaker",
                price = "$79.99",
                rating = "★ 4.4 / 5.0",
                description = "360-degree immersive stereo sound with IPX7 waterproofing."
            )
        }

        findViewById<View>(R.id.card_product_7).setOnClickListener {
            openProduct(
                name = "Fast Wireless Charging Stand",
                price = "$39.99",
                rating = "★ 4.6 / 5.0",
                description = "15W Qi-certified rapid inductive charging dock for phone and buds."
            )
        }

        findViewById<View>(R.id.card_product_8).setOnClickListener {
            openProduct(
                name = "Ergonomic Desk Chair",
                price = "$329.00",
                rating = "★ 4.7 / 5.0",
                description = "Breathable mesh back with adjustable lumbar support and headrest."
            )
        }
    }

    private fun openProduct(name: String, price: String, rating: String, description: String) {
        val intent = Intent(this, ProductActivity::class.java).apply {
            putExtra("PRODUCT_NAME", name)
            putExtra("PRODUCT_PRICE", price)
            putExtra("PRODUCT_RATING", rating)
            putExtra("PRODUCT_DESC", description)
        }
        startActivity(intent)
    }
}

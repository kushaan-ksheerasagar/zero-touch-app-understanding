package com.zerotouch.demo

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class ResultsActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_results)

        findViewById<Button>(R.id.btn_back).setOnClickListener {
            finish()
        }

        val query = intent.getStringExtra("SEARCH_QUERY") ?: "Headphones"
        val textTitle = findViewById<TextView>(R.id.text_results_title)
        textTitle.text = "Results: $query"

        val textCount = findViewById<TextView>(R.id.text_results_count)
        textCount.text = "Found 4 products for '$query'"

        // Result Card 1
        findViewById<View>(R.id.result_card_1).setOnClickListener {
            openProduct(
                name = "Wireless Over-Ear Headphones",
                price = "$129.99",
                rating = "★ 4.5 / 5.0",
                description = "Premium studio sound with custom 40mm neodymium drivers and active noise cancellation."
            )
        }

        // Result Card 2
        findViewById<View>(R.id.result_card_2).setOnClickListener {
            openProduct(
                name = "Studio Monitor Headphones",
                price = "$199.00",
                rating = "★ 4.8 / 5.0",
                description = "Flat frequency response engineered for critical listening, podcasting, and audio mixing."
            )
        }

        // Result Card 3
        findViewById<View>(R.id.result_card_3).setOnClickListener {
            openProduct(
                name = "Compact Sport Earbuds",
                price = "$59.99",
                rating = "★ 4.2 / 5.0",
                description = "IPX7 waterproof rating with secure ear hooks and 24-hour total playback with charging case."
            )
        }

        // Result Card 4
        findViewById<View>(R.id.result_card_4).setOnClickListener {
            openProduct(
                name = "Noise Isolating Earphones",
                price = "$39.50",
                rating = "★ 4.0 / 5.0",
                description = "Ergonomic in-ear design with reinforced braided cable and built-in hands-free microphone."
            )
        }

        // Result Card 5
        findViewById<View>(R.id.result_card_5).setOnClickListener {
            openProduct(
                name = "Open-Ear Sport Headphones",
                price = "$149.00",
                rating = "★ 4.6 / 5.0",
                description = "Bone-conduction transducers with ambient situational awareness."
            )
        }

        // Result Card 6
        findViewById<View>(R.id.result_card_6).setOnClickListener {
            openProduct(
                name = "Studio DJ Over-Ear Monitors",
                price = "$179.99",
                rating = "★ 4.7 / 5.0",
                description = "Swiveling earcups with high-power handling and coiled detachable cable."
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

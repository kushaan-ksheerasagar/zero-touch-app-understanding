package com.zerotouch.demo

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class ProductActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_product)

        findViewById<Button>(R.id.btn_back).setOnClickListener {
            finish()
        }

        val name = intent.getStringExtra("PRODUCT_NAME") ?: "Wireless Headphones"
        val price = intent.getStringExtra("PRODUCT_PRICE") ?: "$129.99"
        val rating = intent.getStringExtra("PRODUCT_RATING") ?: "★ 4.5 / 5.0"
        val desc = intent.getStringExtra("PRODUCT_DESC")
            ?: "Designed for immersive listening with custom-tuned 40mm drivers and active noise cancellation."

        findViewById<TextView>(R.id.text_product_name).text = name
        findViewById<TextView>(R.id.text_product_price).text = price
        findViewById<TextView>(R.id.text_product_rating).text = rating
        findViewById<TextView>(R.id.text_product_description).text = desc
    }
}

package com.zerotouch.demo

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import androidx.appcompat.app.AppCompatActivity

class SearchActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_search)

        val btnBack = findViewById<Button>(R.id.btn_back)
        val inputSearch = findViewById<EditText>(R.id.input_search)
        val btnDoSearch = findViewById<Button>(R.id.btn_do_search)

        btnBack.setOnClickListener {
            finish()
        }

        inputSearch.setOnEditorActionListener { _, _, _ ->
            btnDoSearch.performClick()
            true
        }

        btnDoSearch.setOnClickListener {
            val imm = getSystemService(INPUT_METHOD_SERVICE) as? android.view.inputmethod.InputMethodManager
            imm?.hideSoftInputFromWindow(currentFocus?.windowToken, 0)
            val query = inputSearch.text.toString().trim()
            val resolvedQuery = if (query.isNotEmpty()) query else "Headphones"
            launchResults(resolvedQuery)
        }

        // Quick category suggestion chips
        findViewById<Button>(R.id.chip_headphones).setOnClickListener {
            launchResults("Headphones")
        }

        findViewById<Button>(R.id.chip_watches).setOnClickListener {
            launchResults("Smart Watches")
        }

        findViewById<Button>(R.id.chip_keyboards).setOnClickListener {
            launchResults("Keyboards")
        }

        findViewById<Button>(R.id.chip_monitors).setOnClickListener {
            launchResults("Monitors")
        }
    }

    private fun launchResults(query: String) {
        val intent = Intent(this, ResultsActivity::class.java).apply {
            putExtra("SEARCH_QUERY", query)
        }
        startActivity(intent)
    }
}

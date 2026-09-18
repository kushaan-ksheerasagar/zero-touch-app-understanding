package com.zerotouch.demo

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class LoginActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        val inputEmail = findViewById<EditText>(R.id.input_email)
        val inputPassword = findViewById<EditText>(R.id.input_password)
        val btnLogin = findViewById<Button>(R.id.btn_login)

        inputPassword.setOnEditorActionListener { _, actionId, _ ->
            btnLogin.performClick()
            true
        }

        btnLogin.setOnClickListener {
            val imm = getSystemService(INPUT_METHOD_SERVICE) as? android.view.inputmethod.InputMethodManager
            imm?.hideSoftInputFromWindow(currentFocus?.windowToken, 0)

            val email = inputEmail.text.toString().trim()
            val password = inputPassword.text.toString().trim()

            // In demo mode, accept any credentials, defaulting if empty
            val resolvedEmail = if (email.isNotEmpty()) email else "demo.user@zerotouch.app"

            val intent = Intent(this, HomeActivity::class.java).apply {
                putExtra("USER_EMAIL", resolvedEmail)
            }
            startActivity(intent)
            finish()
        }
    }
}

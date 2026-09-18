package com.zerotouch.demo

import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class ProfileActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_profile)

        findViewById<Button>(R.id.btn_back).setOnClickListener {
            finish()
        }

        findViewById<View>(R.id.row_account).setOnClickListener {
            Toast.makeText(this, "Account details opened", Toast.LENGTH_SHORT).show()
        }

        findViewById<View>(R.id.row_notifications).setOnClickListener {
            Toast.makeText(this, "Notification preferences opened", Toast.LENGTH_SHORT).show()
        }

        findViewById<View>(R.id.row_privacy).setOnClickListener {
            Toast.makeText(this, "Privacy settings opened", Toast.LENGTH_SHORT).show()
        }

        findViewById<View>(R.id.row_about).setOnClickListener {
            Toast.makeText(this, "ZeroTouch Demo v1.0", Toast.LENGTH_SHORT).show()
        }
    }
}

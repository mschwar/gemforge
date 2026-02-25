package __ANDROID_PACKAGE__

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    private var tapCount: Int = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val counterText = findViewById<TextView>(R.id.counterText)
        val actionButton = findViewById<Button>(R.id.incrementButton)

        actionButton.setOnClickListener {
            tapCount += 1
            counterText.text = "Core feature count: $tapCount"
        }
    }
}

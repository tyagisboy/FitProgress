package com.fitprogress.app

import android.app.Application
import com.fitprogress.app.data.FitProgressDatabase

class FitProgressApp : Application() {
    val database: FitProgressDatabase by lazy { FitProgressDatabase.get(this) }
}

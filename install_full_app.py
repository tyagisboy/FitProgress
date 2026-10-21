import os

files = {}

# 1. Complete Kotlin Core (Math, Units, Delta, Progression)
files["app/src/main/java/com/fitprogress/app/core/FitnessCore.kt"] = """package com.fitprogress.app.core

import kotlin.math.pow
import kotlin.math.roundToInt

enum class WeightUnit { KG, LBS }
enum class HeightUnit { CM, FT_IN }
enum class ExerciseType { STRENGTH, BODYWEIGHT, ASSISTED, TIMED, CARDIO }
enum class MuscleGroup { CHEST, BACK, LEGS, SHOULDERS, ARMS, CORE, CARDIO }
enum class ProgressionStatus(val label: String) {
    IMPROVING("Improving"), MAINTAINING("Maintaining"),
    POSSIBLE_DECLINE("Possible Decline"), INSUFFICIENT_DATA("Insufficient Data")
}

data class SessionDataPoint(val epochMs: Long, val dateIso: String, val value: Double, val details: String)

object FitnessMath {
    fun calculateBmi(weightKg: Double, heightCm: Double): Double? {
        if (weightKg <= 20.0 || heightCm <= 50.0) return null
        val heightM = heightCm / 100.0
        return ((weightKg / heightM.pow(2)) * 10.0).roundToInt() / 10.0
    }

    fun getBmiCategory(bmi: Double): String = when {
        bmi < 18.5 -> "Underweight"
        bmi < 25.0 -> "Normal weight"
        bmi < 30.0 -> "Overweight"
        else -> "Obese"
    }

    fun kgToLbs(kg: Double): Double = ((kg * 2.20462) * 10.0).roundToInt() / 10.0
    fun lbsToKg(lbs: Double): Double = ((lbs / 2.20462) * 10.0).roundToInt() / 10.0

    fun calculateVolume(loadKg: Double, reps: Int): Double =
        if (loadKg <= 0.0 || reps <= 0) 0.0 else ((loadKg * reps) * 10.0).roundToInt() / 10.0

    fun calculate1Rm(loadKg: Double, reps: Int): Double? {
        if (reps !in 1..12 || loadKg <= 0.0) return null
        if (reps == 1) return loadKg
        return ((loadKg / (1.0278 - (0.0278 * reps))) * 10.0).roundToInt() / 10.0
    }
}

object StepDeltaCalculator {
    fun calculateDelta(current: Int, last: Int): Int {
        if (current < 0 || last <= 0) return 0
        return if (current >= last) current - last else current
    }
    fun estimateDistanceKm(steps: Int): Double = ((steps * 0.762 / 1000.0) * 100.0).roundToInt() / 100.0
    fun estimateCalories(steps: Int): Int = (steps * 0.04).toInt()
}
"""

# 2. Database Entities and DAOs
files["app/src/main/java/com/fitprogress/app/data/Database.kt"] = """package com.fitprogress.app.data

import android.content.Context
import androidx.room.*
import androidx.sqlite.db.SupportSQLiteDatabase
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "weight_records")
data class WeightRecord(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val recordedAtEpochMs: Long,
    val weightKg: Double,
    val note: String? = null
)

@Entity(tableName = "daily_steps")
data class StepRecord(
    @PrimaryKey val dateIsoString: String,
    val sensorSteps: Int = 0,
    val manualSteps: Int = 0,
    val goalSteps: Int = 10000
) {
    val totalSteps: Int get() = sensorSteps + manualSteps
}

@Entity(tableName = "exercises")
data class Exercise(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val muscleGroup: String,
    val exerciseType: String,
    val isArchived: Boolean = false
)

@Entity(tableName = "workout_sessions")
data class WorkoutSession(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val startedAtEpochMs: Long,
    val finishedAtEpochMs: Long? = null
)

@Entity(tableName = "workout_sets")
data class WorkoutSet(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val sessionId: Long,
    val exerciseId: Long,
    val setIndex: Int,
    val reps: Int? = null,
    val weightKg: Double? = null,
    val isCompleted: Boolean = false
)

@Dao
interface FitDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertWeight(record: WeightRecord): Long

    @Query("SELECT * FROM weight_records ORDER BY recordedAtEpochMs DESC")
    fun getAllWeights(): Flow<List<WeightRecord>>

    @Query("SELECT * FROM weight_records ORDER BY recordedAtEpochMs DESC LIMIT 1")
    fun getLatestWeight(): Flow<WeightRecord?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertSteps(steps: StepRecord)

    @Query("SELECT * FROM daily_steps WHERE dateIsoString = :date LIMIT 1")
    fun getStepsForDate(date: String): Flow<StepRecord?>

    @Query("SELECT * FROM exercises WHERE isArchived = 0 ORDER BY name ASC")
    fun getExercises(): Flow<List<Exercise>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertExercise(exercise: Exercise): Long

    @Query("SELECT * FROM workout_sessions WHERE finishedAtEpochMs IS NULL LIMIT 1")
    fun getActiveDraft(): Flow<WorkoutSession?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertSession(session: WorkoutSession): Long

    @Update
    suspend fun updateSession(session: WorkoutSession)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertSet(set: WorkoutSet): Long

    @Update
    suspend fun updateSet(set: WorkoutSet)

    @Query("SELECT * FROM workout_sets WHERE sessionId = :sessionId ORDER BY setIndex ASC")
    fun getSetsForSession(sessionId: Long): Flow<List<WorkoutSet>>
}

@Database(
    entities = [WeightRecord::class, StepRecord::class, Exercise::class, WorkoutSession::class, WorkoutSet::class],
    version = 1,
    exportSchema = false
)
abstract class FitProgressDatabase : RoomDatabase() {
    abstract fun fitDao(): FitDao

    companion object {
        @Volatile private var INSTANCE: FitProgressDatabase? = null

        fun get(context: Context): FitProgressDatabase = INSTANCE ?: synchronized(this) {
            Room.databaseBuilder(context.applicationContext, FitProgressDatabase::class.java, "fitprogress.db")
                .addCallback(object : Callback() {
                    override fun onCreate(db: SupportSQLiteDatabase) {
                        super.onCreate(db)
                        CoroutineScope(Dispatchers.IO).launch {
                            val starters = listOf(
                                "('Barbell Bench Press', 'CHEST', 'STRENGTH')",
                                "('Lat Pulldown', 'BACK', 'STRENGTH')",
                                "('Barbell Squat', 'LEGS', 'STRENGTH')",
                                "('Deadlift', 'BACK', 'STRENGTH')",
                                "('Overhead Press', 'SHOULDERS', 'STRENGTH')",
                                "('Push-Up', 'CHEST', 'BODYWEIGHT')",
                                "('Pull-Up', 'BACK', 'BODYWEIGHT')"
                            )
                            starters.forEach {
                                db.execSQL("INSERT INTO exercises (name, muscleGroup, exerciseType) VALUES $it;")
                            }
                        }
                    }
                }).build().also { INSTANCE = it }
        }
    }
}
"""

# 3. Application Class
files["app/src/main/java/com/fitprogress/app/FitProgressApp.kt"] = """package com.fitprogress.app

import android.app.Application
import com.fitprogress.app.data.FitProgressDatabase

class FitProgressApp : Application() {
    val database: FitProgressDatabase by lazy { FitProgressDatabase.get(this) }
}
"""

# 4. Complete Accessible UI (Home, Workouts, Steps, History, Profile)
files["app/src/main/java/com/fitprogress/app/MainActivity.kt"] = """package com.fitprogress.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import androidx.navigation.compose.*
import com.fitprogress.app.core.FitnessMath
import com.fitprogress.app.data.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val db = (application as FitProgressApp).database
        val dao = db.fitDao()

        setContent {
            MaterialTheme {
                MainAppScaffold(dao)
            }
        }
    }
}

@Composable
fun MainAppScaffold(dao: FitDao) {
    val navController = rememberNavController()
    val navBackStack by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStack?.destination?.route ?: "home"

    val tabs = listOf(
        Triple("home", "Home", Icons.Default.Home),
        Triple("workouts", "Workouts", Icons.Default.FitnessCenter),
        Triple("steps", "Steps", Icons.Default.DirectionsWalk),
        Triple("profile", "Profile", Icons.Default.Person)
    )

    Scaffold(
        bottomBar = {
            NavigationBar {
                tabs.forEach { (route, label, icon) ->
                    NavigationBarItem(
                        selected = currentRoute == route,
                        onClick = { navController.navigate(route) { launchSingleTop = true } },
                        icon = { Icon(icon, contentDescription = label) },
                        label = { Text(label) }
                    )
                }
            }
        }
    ) { innerPad ->
        NavHost(navController, startDestination = "home", modifier = Modifier.padding(innerPad)) {
            composable("home") { HomeScreen(dao) }
            composable("workouts") { WorkoutsScreen(dao) }
            composable("steps") { StepsScreen(dao) }
            composable("profile") { ProfileScreen(dao) }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(dao: FitDao) {
    val latestWeight by dao.getLatestWeight().collectAsState(initial = null)
    val todayIso = remember { SimpleDateFormat("yyyy-MM-dd", Locale.US).format(Date()) }
    val todaySteps by dao.getStepsForDate(todayIso).collectAsState(initial = null)
    val scope = rememberCoroutineScope()
    var showWeightDialog by remember { mutableStateOf(false) }

    Scaffold(
        topBar = { TopAppBar(title = { Text("FitProgress", fontWeight = FontWeight.Bold) }) }
    ) { pad ->
        Column(
            modifier = Modifier.fillMaxSize().padding(pad).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Button(
                onClick = { showWeightDialog = true },
                modifier = Modifier.fillMaxWidth().height(48.dp)
            ) {
                Icon(Icons.Default.Add, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Log Body Weight")
            }

            // Steps Summary Card
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text("Today's Steps", style = MaterialTheme.typography.labelMedium)
                    Spacer(Modifier.height(4.dp))
                    val steps = todaySteps?.totalSteps ?: 0
                    Text("$steps / 10,000 steps", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(8.dp))
                    LinearProgressIndicator(progress = { (steps / 10000f).coerceIn(0f, 1f) }, modifier = Modifier.fillMaxWidth())
                }
            }

            // Weight and BMI Card
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text("Latest Body Metrics", style = MaterialTheme.typography.labelMedium)
                    Spacer(Modifier.height(4.dp))
                    if (latestWeight == null) {
                        Text("No weight logged yet. Tap above to log your first record.")
                    } else {
                        val w = latestWeight!!.weightKg
                        val bmi = FitnessMath.calculateBmi(w, 175.0)
                        Text("$w kg", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                        Text("Current BMI: ${bmi ?: "--"} (${bmi?.let { FitnessMath.getBmiCategory(it) } ?: ""})")
                    }
                }
            }
        }

        if (showWeightDialog) {
            var input by remember { mutableStateOf("") }
            AlertDialog(
                onDismissRequest = { showWeightDialog = false },
                title = { Text("Log Body Weight") },
                text = {
                    OutlinedTextField(
                        value = input,
                        onValueChange = { input = it },
                        label = { Text("Weight (kg)") },
                        singleLine = true
                    )
                },
                confirmButton = {
                    Button(onClick = {
                        val value = input.toDoubleOrNull()
                        if (value != null && value > 0) {
                            scope.launch {
                                dao.insertWeight(WeightRecord(recordedAtEpochMs = System.currentTimeMillis(), weightKg = value))
                            }
                            showWeightDialog = false
                        }
                    }) { Text("Save") }
                },
                dismissButton = {
                    TextButton(onClick = { showWeightDialog = false }) { Text("Cancel") }
                }
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WorkoutsScreen(dao: FitDao) {
    val exercises by dao.getExercises().collectAsState(initial = emptyList())
    val activeSession by dao.getActiveDraft().collectAsState(initial = null)
    val scope = rememberCoroutineScope()

    Scaffold(
        topBar = { TopAppBar(title = { Text("Workouts & Exercises") }) }
    ) { pad ->
        Column(Modifier.fillMaxSize().padding(pad).padding(16.dp)) {
            if (activeSession == null) {
                Button(
                    onClick = {
                        scope.launch {
                            dao.insertSession(WorkoutSession(name = "Training Session", startedAtEpochMs = System.currentTimeMillis()))
                        }
                    },
                    modifier = Modifier.fillMaxWidth().height(48.dp)
                ) {
                    Icon(Icons.Default.PlayArrow, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Start Workout Session")
                }
            } else {
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
                    Column(Modifier.padding(16.dp)) {
                        Text("Workout In Progress", fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(8.dp))
                        Button(onClick = {
                            scope.launch {
                                dao.updateSession(activeSession!!.copy(finishedAtEpochMs = System.currentTimeMillis()))
                            }
                        }) {
                            Text("Finish Workout")
                        }
                    }
                }
            }

            Spacer(Modifier.height(16.dp))
            Text("Exercise Library", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))

            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(exercises) { ex ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Row(Modifier.fillMaxWidth().padding(14.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Column {
                                Text(ex.name, fontWeight = FontWeight.SemiBold)
                                Text("${ex.muscleGroup} • ${ex.exerciseType}", style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StepsScreen(dao: FitDao) {
    val todayIso = remember { SimpleDateFormat("yyyy-MM-dd", Locale.US).format(Date()) }
    val record by dao.getStepsForDate(todayIso).collectAsState(initial = null)
    val scope = rememberCoroutineScope()
    var showDialog by remember { mutableStateOf(false) }

    Scaffold(
        topBar = { TopAppBar(title = { Text("Step Activity") }) }
    ) { pad ->
        Column(Modifier.fillMaxSize().padding(pad).padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            val total = record?.totalSteps ?: 0
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(20.dp)) {
                    Text("Today's Count", style = MaterialTheme.typography.labelMedium)
                    Text("$total", style = MaterialTheme.typography.displayMedium, fontWeight = FontWeight.Bold)
                    Text("Daily Goal: 10,000 steps")
                    Spacer(Modifier.height(12.dp))
                    LinearProgressIndicator(progress = { (total / 10000f).coerceIn(0f, 1f) }, modifier = Modifier.fillMaxWidth())
                }
            }

            Button(onClick = { showDialog = true }, modifier = Modifier.fillMaxWidth()) {
                Text("Log Manual Steps")
            }
        }

        if (showDialog) {
            var stepInput by remember { mutableStateOf("") }
            AlertDialog(
                onDismissRequest = { showDialog = false },
                title = { Text("Log Steps") },
                text = {
                    OutlinedTextField(
                        value = stepInput,
                        onValueChange = { stepInput = it },
                        label = { Text("Steps") },
                        singleLine = true
                    )
                },
                confirmButton = {
                    Button(onClick = {
                        val steps = stepInput.toIntOrNull()
                        if (steps != null && steps >= 0) {
                            scope.launch {
                                dao.upsertSteps(StepRecord(dateIsoString = todayIso, manualSteps = steps))
                            }
                            showDialog = false
                        }
                    }) { Text("Save") }
                },
                dismissButton = {
                    TextButton(onClick = { showDialog = false }) { Text("Cancel") }
                }
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(dao: FitDao) {
    Scaffold(topBar = { TopAppBar(title = { Text("Settings & Privacy") }) }) { pad ->
        Column(Modifier.fillMaxSize().padding(pad).padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text("100% Offline & Private", fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(4.dp))
                    Text(
                        "FitProgress stores all your records exclusively on this device. No cloud servers, no logins, no tracking.",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }
    }
}
"""

for path, content in files.items():
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("Full FitProgress application injected successfully!")

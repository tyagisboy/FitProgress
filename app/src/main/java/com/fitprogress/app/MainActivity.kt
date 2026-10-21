package com.fitprogress.app

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

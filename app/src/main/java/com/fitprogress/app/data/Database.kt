package com.fitprogress.app.data

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
                                "('Barbell Bench Press', 'CHEST', 'STRENGTH', 0)",
                                "('Lat Pulldown', 'BACK', 'STRENGTH', 0)",
                                "('Barbell Squat', 'LEGS', 'STRENGTH', 0)",
                                "('Deadlift', 'BACK', 'STRENGTH', 0)",
                                "('Overhead Press', 'SHOULDERS', 'STRENGTH', 0)",
                                "('Push-Up', 'CHEST', 'BODYWEIGHT', 0)",
                                "('Pull-Up', 'BACK', 'BODYWEIGHT', 0)"
                            )
                            starters.forEach {
                                db.execSQL("INSERT INTO exercises (name, muscleGroup, exerciseType, isArchived) VALUES $it;")
                            }
                        }
                    }
                }).build().also { INSTANCE = it }
        }
    }
}

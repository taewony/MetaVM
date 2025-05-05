DataSource: Titanic {
    load_csv("titanic.csv")
}

Transform: PassengerStats {
    input = Titanic
    metrics = ["Age:mean", "Fare:std", "Survived:median"]
}

Print: Results {
    title = "탑승객 통계 분석"
    format = table
    data = PassengerStats
}
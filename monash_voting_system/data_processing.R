install.packages("dplyr")
install.packages("tidyr")
library(dplyr)
library(tidyr)

# Read the dataset from the CSV file
data <- read.csv("FIT3163 dataset.csv")

# Create user file with Student ID, First Name, and Last Name
user <- data[, c("Student.ID", "F.Name", "L.Name")]


# Create the user profile file with user information
user_profile <- data[, c("Student.ID", "Gender", "DOB", "Faculty", "Level.of.Education", "Campus.Location")]
# Recode gender to match database
user_profile$Gender <- recode(user_profile$Gender, "F" = "Female", "M" = "Male", "O" = "Other")
# Recode the Level of Education column because PhD belongs to Postgraduate
user_profile$Level.of.Education <- recode(data$Level.of.Education, "PhD" = "Postgraduate")


# Create the memberships file with Student ID and Clubs columns
memberships <- data[, c("Student.ID", "Clubs")]
# Split the Clubs column into separate rows
memberships<-separate_rows(memberships, Clubs,sep=",\\s*")
# Remove empty or NA rows
memberships <- memberships [memberships$Clubs != "" & !is.na(memberships$Clubs),]

# Save files as csv
write.csv(user, "Users.csv", row.names = FALSE)
write.csv(user_profile, "User Profiles.csv", row.names = FALSE)
write.csv(memberships, "Memberships.csv", row.names = FALSE)


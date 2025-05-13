import express from "express";
import {dirname} from "path";
import {fileURLToPath} from "url";
import pg from "pg";
import dotenv from "dotenv";


const app = express();
const __dirname = dirname(fileURLToPath(import.meta.url));
const port = process.env.PORT || 3000;
dotenv.config({ path: __dirname + "/.env" });

app.use(express.static(__dirname + '/public'));
app.use(express.urlencoded({ extended: true }));
app.set("views", __dirname + "/../views");

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
})
console.log("tite   ");
app.get('/', (req, res) => {
  res.sendFile(__dirname + '/views/Front.html');
});

app.get('/SignIN', (req, res) => {
    res.sendFile(__dirname + '/views/SignIN.html');
});
  
app.get('/User', (req, res) => {
  res.sendFile(__dirname + '/views/User.html');
});

app.get('/fpass', (req, res) => {
    res.sendFile(__dirname + '/views/fpass.html');
  });

  app.get('/main', (req, res) => {
    res.sendFile(__dirname + '/views/main.html');
  });
  